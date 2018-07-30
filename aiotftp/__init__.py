import asyncio
import urllib.parse

from .packet import Ack, Opcode, Mode, parse, Request
from .protocol import RequestHandler, RequestStreamHandler
from .transfers import StreamReader, FileResponse, Response  # noqa
from .helpers import get_tid


class Server:
    def __init__(self, rrq, wrq, *, timeout=None, loop=None):
        self._loop = None
        self.rrq = rrq
        self.wrq = wrq
        self.timeout = timeout

    def __call__(self):
        return RequestHandler(
            self.rrq, self.wrq, timeout=self.timeout, loop=self._loop)


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
        await self.stream.wait_eof()

    async def data(self):
        payload = bytearray()
        async for chunk in self.stream:
            payload.extend(chunk)
        return bytes(payload)


def read(*args, **kwargs):
    return _Request(*args, **kwargs)
