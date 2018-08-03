import asyncio

from .protocol import OutboundDataProtocol


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
            lambda: OutboundDataProtocol(tid=request.tid, timeout=request.timeout, loop=self._loop),
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
                await response.write(chunk)
                if len(chunk) < 512:
                    break

        self.length = response.output_size
        self._eof_sent = True
        return response

    async def write_eof(self):
        self._writer = None
        self.transport.close()
