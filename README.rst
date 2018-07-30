aiotftp
=======

.. image:: https://travis-ci.org/sangoma/aiotftp.svg?branch=master
   :target: https://travis-ci.org/sangoma/aiotftp
   :align: right
   :alt: Travis status for master branch

.. image:: https://codecov.io/gh/sangoma/aiotftp/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/sangoma/aiotftp
   :alt: codecov.io status for master branch

Why?
----

Because what the world really needed was asynchronous, dynamically
routable TFTP.


Seriously, though: it can be useful for testing, and the intended
use-case is keeping track of the requests our devices make while under
test, and be able to do such testing against potentially many devices
simultaneously.

While it can be used for the usual use case of TFTP (moving files into
or out of some directory) it’s also possible to provide arbitrary
logic to operate on a per-request basis to either

- provide a buffer to use as the response to a RRQ
- recieve a buffer to do whatever you care to after a WRQ complete

Documentation?
--------------

Eventually. Hopefully.

TODO
----

Right now only ``OCTET`` mode is supported; should probably support
``ASCII`` as well.

Getting Started
---------------

Client example:

.. code:: python

   import aiotftp

   async def main(loop):
       async with aiotftp.read('tftp://localhost/pubkey.txt') as response:
           contents = await response.data()
           print(contents.decode())

   loop = asyncio.get_event_loop()
   loop.run_until_complete(main())

Server example:

.. code:: python

   from aiotftp import Server, FileResponse, Response

   async def read(request):
       if request.filename == 'hello':
           return Response(b'Hello World!\n')
       return FileResponse(request.filename)

   async def write(request, transfer):
       with open(request.filename, 'wb') as fp:
           async for chunk in transfer:
               fp.write(chunk)

   async def main(loop):
       server = Server(read, write)
       await loop.create_datagram_endpoint(server, local_addr=(None, 69))

   loop = asyncio.get_event_loop()
   loop.run_until_complete(main())
   loop.run_forever()
