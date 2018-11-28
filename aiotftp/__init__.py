import asyncio
from collections.abc import MutableMapping
import urllib.parse

from .packet import Mode, Opcode, Request
from .protocol import InboundDataProtocol, OutboundDataProtocol
from .response import FileResponse, Response, StreamResponse  # noqa
from .server import RequestHandler
from .streams import StreamReader


class Server(MutableMapping):
    def __init__(self, rrq, wrq, **kwargs):
        self.rrq = rrq
        self.wrq = wrq
        self._state = {}
        self._kwargs = kwargs

    def __call__(self):
        return RequestHandler(self, self.rrq, self.wrq, **self._kwargs)

    def __getitem__(self, key):
        return self._state[key]

    def __setitem__(self, key, value):
        self._state[key] = value

    def __delitem__(self, key):
        del self._state[key]

    def __iter__(self):
        return iter(self._state)

    def __len__(self):
        return len(self._state)


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
            lambda: InboundDataProtocol(
                self.stream, tid=None, loop=self._loop),
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


async def write(resource, data, *, timeout=2.0, local_addr=None, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    url = urllib.parse.urlsplit(resource)
    if url.scheme != 'tftp':
        raise ValueError('Unsupported scheme')

    remote_addr = (url.hostname, url.port or 69)
    local_addr = local_addr or ('0.0.0.0', 0)

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: OutboundDataProtocol(tid=None, timeout=timeout, loop=loop),
        local_addr=local_addr)

    await protocol.start(url.path[1:], remote_addr)

    if isinstance(data, (bytes, bytearray, memoryview)):
        while True:
            chunk, data = data[:512], data[512:]
            await protocol.write(chunk)
            if len(chunk) < 512:
                break

    else:
        while True:
            chunk = data.read(512)
            await protocol.write(chunk)
            if len(chunk) < 512:
                break
