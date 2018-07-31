import asyncio
import collections
from typing import Optional

from .helpers import set_result, set_exception


class AsyncStreamIterator:
    def __init__(self, read_func) -> None:
        self.read_func = read_func

    def __aiter__(self) -> 'AsyncStreamIterator':
        return self

    async def __anext__(self) -> bytes:
        chunk = await self.read_func()
        if not chunk:
            raise StopAsyncIteration
        return chunk


class StreamReader:
    total_bytes = 0

    def __init__(self, *, timer=None, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._size = 0
        self._cursor = 0
        self._buffer = collections.deque()
        self._buffer_offset = 0
        self._eof = False
        self._waiter = None
        self._eof_waiter = None
        self._exception = None
        self._timer = timer

    def exception(self) -> Optional[BaseException]:
        return self._exception

    def set_exception(self, exc: BaseException) -> None:
        self._exception = exc

        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            set_exception(waiter, exc)

        waiter = self._eof_waiter
        if waiter is not None:
            set_exception(waiter, exc)
            self._eof_waiter = None

    def feed_eof(self) -> None:
        self._eof = True

        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            set_result(waiter, True)

        waiter = self._eof_waiter
        if waiter is not None:
            self._eof_waiter = None
            set_result(waiter, True)

    def is_eof(self) -> bool:
        return self._eof

    def at_eof(self) -> bool:
        return self._eof and not self._buffer

    async def wait_eof(self) -> None:
        if self._eof:
            return

        assert self._eof_waiter is None
        self._eof_waiter = self._loop.create_future()
        try:
            await self._eof_waiter
        finally:
            self._eof_waiter = None

    def feed_data(self, data) -> None:
        assert not self._eof, 'feed_data after feed_eof'

        if not data:
            return

        self._size += len(data)
        self._buffer.append(data)
        self.total_bytes += len(data)

        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            set_result(waiter, False)

    async def read(self, n: int = -1) -> bytes:
        if self._exception is not None:
            raise self._exception

        if not self._buffer and not self._eof:
            await self._wait('readany')

        return self._read_nowait(-1)

    def read_nowait(self) -> bytes:
        if self._exception is not None:
            raise self._exception

        if self._waiter and not self._waiter.done():
            raise RuntimeError(
                'Called while some coroutine is waiting for incoming data.')

        return self._read_nowait(n)

    def _read_nowait_chunk(self, n):
        first_buffer = self._buffer[0]
        offset = self._buffer_offset
        if n != -1 and len(first_buffer) - offset > n:
            data = first_buffer[offset:offset + n]
            self._buffer_offset += n

        elif offset:
            self._buffer.popleft()
            data = first_buffer[offset:]
            self._buffer_offset = 0

        else:
            data = self._buffer.popleft()

        self._size -= len(data)
        self._cursor += len(data)
        return data

    def _read_nowait(self, n):
        chunks = []

        while self._buffer:
            chunk = self._read_nowait_chunk(n)
            chunks.append(chunk)
            if n != -1:
                n -= len(chunk)
                if n == 0:
                    break

        return b''.join(chunks) if chunks else b''

    async def _wait(self, func_name):
        if self._waiter is not None:
            raise RuntimeError(
                '{} called while another coroutine is '
                'already waiting for incoming data'.format(func_name))

        waiter = self._waiter = self._loop.create_future()
        try:
            if self._timer:
                with self._timer:
                    await waiter
            else:
                await waiter
        finally:
            self._waiter = None

    def __aiter__(self):
        return AsyncStreamIterator(self.read)
