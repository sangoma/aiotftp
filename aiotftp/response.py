import asyncio

from .helpers import get_tid, set_result
from .packet import Ack, Error, Data, ErrorCode, Mode, Opcode, parse


class ReadRequestHandler(asyncio.DatagramProtocol):
    def __init__(self, *, timeout=None, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._timeout = timeout or 2.0

        self._blockid = 0
        self._waiter = None

        self.output_size = 0

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        packet = parse(data)
        if packet.opcode == Opcode.ACK and packet.block_no == self._blockid:
            waiter = self._waiter
            if waiter is not None:
                self._waiter = None
                set_result(waiter, False)

    async def write(self, chunk) -> None:
        self._blockid += 1
        if self._blockid > 65535:
            self._blockid = 0

        packet = bytes(Data(block_no=self._blockid, data=chunk))

        async def sendto_forever():
            self.output_size += len(chunk)
            while True:
                self.transport.sendto(packet)
                await asyncio.sleep(self._timeout)

        try:
            coro = asyncio.ensure_future(sendto_forever())
            await self._wait('write')
        finally:
            coro.cancel()

        if len(chunk) < 512:
            self.transport.close()

    async def _wait(self, func_name):
        if self._waiter is not None:
            raise RuntimeError(
                '{} called while another coroutine is '
                'already waiting for incoming data'.format(func_name))

        waiter = self._waiter = self._loop.create_future()
        try:
            await waiter
        finally:
            self._waiter = None


class StreamResponse:
    def __init__(self, *, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._writer = None
        self._buffer = bytearray()
        self._eof_sent = False
        self._timeout = 2.0

        self.length = None

    async def prepare(self, request):
        if self._eof_sent:
            return
        if self._writer is not None:
            return self._writer

        transport, protocol = await self._loop.create_datagram_endpoint(
            lambda: ReadRequestHandler(timeout=self._timeout, loop=self._loop),
            remote_addr=request.tid)

        self.transport = transport
        self._writer = protocol
        return protocol

    async def write(self, data):
        assert isinstance(data, (bytes, bytearray, memoryview)), \
            "data argument must be byte-ish (%r)" % type(data)

        if self._eof_sent:
            raise RuntimeError("Cannot call write() after write_eof()")
        if self._writer is None:
            raise RuntimeError("Cannot call write() before prepare()")

        self._buffer.extend(data)

        while len(self._buffer) >= 512:
            chunk, self._buffer = self._buffer[:512], self._buffer[512:]
            await self._writer.write(chunk)

    async def write_eof(self):
        if self._eof_sent:
            return
        if self._writer is None:
            raise RuntimeError("Cannot call write_eof() before prepare()")

        while len(self._buffer) >= 512:
            chunk, self._buffer = self._buffer[:512], self._buffer[512:]
            await self._writer.write(chunk)
        await self._writer.write(self._buffer)

        self.length = self._writer.output_size
        self._eof_sent = True
        self._writer = None
        self.transport.close()


class Response(StreamResponse):
    def __init__(self, data):
        super().__init__()

        assert isinstance(data, (bytes, bytearray, memoryview)), \
            "data argument must be byte-ish (%r)" % type(data)
        self._buffer = data


class FileResponse(StreamResponse):
    def __init__(self, path):
        super().__init__()

        self._path = path

    async def prepare(self, request):
        response = await super().prepare(request)

        with open(self._path, 'rb') as fobj:
            while True:
                chunk = fobj.read(request.chunk_size)
                if not chunk:
                    break
                await response.write(chunk)

        self.length = response.output_size
        self._eof_sent = True
        return response

    async def write_eof(self):
        self._writer = None
        self.transport.close()
