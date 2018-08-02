import asyncio
import urllib.parse

from .packet import Ack, Mode, Opcode, Request, parse  # noqa
from .response import FileResponse, Response, StreamResponse  # noqa
from .server import RequestHandler, RequestStreamHandler
from .streams import StreamReader


class Server:
    def __init__(self, rrq, wrq, **kwargs):
        self.rrq = rrq
        self.wrq = wrq
        self._kwargs = kwargs

    def __call__(self):
        return RequestHandler(
            self.rrq, self.wrq, **self._kwargs)


class _Request:
    def __init__(self, resource, local_addr=None, *, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self.stream = StreamReader()

        url = urllib.parse.urlsplit(resource)
        if url.scheme != 'tftp':
            raise ValueError('Unsupported scheme')

        self.request = Request(
            Opcode.RRQ, filename=url.path[1:], mode=Mode.OCTET)
        self.remote_addr = (url.hostname, url.port or 69)
        self.local_addr = local_addr or ('0.0.0.0', 0)

    async def __aenter__(self):
        transport, protocol = await self._loop.create_datagram_endpoint(
            lambda: RequestStreamHandler(self.stream, loop=self._loop),
            local_addr=self.local_addr)

        transport.sendto(bytes(self.request), self.remote_addr)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if not exc_type:
            await self.stream.wait_eof()

    async def data(self):
        payload = bytearray()
        async for chunk in self.stream:
            payload.extend(chunk)
        return bytes(payload)


def read(*args, **kwargs):
    return _Request(*args, **kwargs)
