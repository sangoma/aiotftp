import asyncio
from operator import itemgetter

from aiotftp import Server, Response
from aiotftp.server import Request
from async_generator import yield_, async_generator
import pytest


FILES = {
    'small_file': b'\x01small\x02',
    'large_file': b'a' * 1000,
    'small_aligned_file': b'a' * 512,
    'large_aligned_file': b'a' * 1024,
}


@pytest.fixture(params=list(FILES.items()), ids=itemgetter(0))
def files(request):
    return request.param


@pytest.fixture
def filename(files):
    return files[0]


@pytest.fixture
def contents(files):
    return files[1]


@pytest.fixture
@async_generator
async def server(event_loop):
    Request.timeout = 0.5

    class Runner:
        def __init__(self):
            self.rrq_files = {filename: asyncio.Future() for filename in FILES}
            self.wrq_files = {filename: asyncio.Future() for filename in FILES}

        async def rrq(self, request):
            try:
                contents = FILES[request.filename]
            except KeyError:
                raise FileNotFoundError(request.filename)

            self.rrq_files[request.filename].set_result(None)
            return Response(data=contents)

        async def wrq(self, request):
            try:
                future = self.wrq_files[request.filename]
            except KeyError:
                raise FileNotFoundError(request.filename)

            payload = bytearray()
            async for chunk in await request.accept():
                payload.extend(chunk)

            return future.set_result(payload)

    runner = Runner()
    server = Server(runner.rrq, runner.wrq)
    _, protocol = await event_loop.create_datagram_endpoint(
        server, local_addr=('127.0.0.1', 1069))

    await yield_(runner)
    await protocol.shutdown(timeout=2)
