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

## Examples?

```python
import asyncio
import io
from aiotftp import TftpRouter
from aiotftp import TftpProtocol


class Router(TftpRouter):
    def rrq_recieved(self, packet, remote):
        return io.BytesIO(b"some file contents\nsome new line\n")

    def rrq_complete(self):
        print("read request completed successfully")

    def wrq_recieved(self, packet, remote):
        return io.BytesIO()

    def wrq_complete(self, buffer):
        buffer.seek(0)
        print(f"got: `{buffer.read(2048)}` from write request")


router = Router()
loop = asyncio.get_event_loop()
listen = loop.create_datagram_endpoint(
    lambda: TftpProtocol(router),
    ("127.0.0.1", 69))
transport, protocol = loop.run_until_complete(listen)

try:
    loop.run_forever()
finally:
    transport.close()
    loop.close()
```
