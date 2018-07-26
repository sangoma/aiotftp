[![Build Status](https://travis-ci.org/sangoma/aiotftp.svg?branch=master)](https://travis-ci.org/sangoma/aiotftp)

aiotftp
=======

## Why?

Because what the world really needed was asynchronous, dynamically
routable TFTP.

Seriously, though: it can be useful for testing, and the intended use-case
is keeping track of the requests our devices make while under test, and
be able to do such testing against potentially many devices simultaneously.

While it can be used for the usual use case of TFTP (moving files into or
out of some directory) it's also possible to provide arbitrary logic to
operate on a per-request basis to either

* provide a buffer to use as the response to a RRQ
* recieve a buffer to do whatever you care to after a WRQ complete

## Documentation?

Eventually. Hopefully.

## TODO

Right now only `OCTET` mode is supported; should probably support `ASCII` as well.

## Examples?

```python
import asyncio

from aiotftp import Server, FileResponse, Response


async def rrq(request):
    if request.filename == 'hello':
        return Response(b'Hello World!\n')
    return FileResponse(request.filename)


async def wrq(request, transfer):
    with open(request.filename, 'wb') as fp:
        async for chunk in transfer:
            fp.write(chunk)


async def main(loop):
    server = Server(rrq, wrq)
    await loop.create_datagram_endpoint(server, local_addr=('0.0.0.0', 69))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main(loop))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    loop.close()
```
