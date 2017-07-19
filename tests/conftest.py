import asyncio
import io
import pytest
from aiotftp import TftpRouter
from aiotftp import create_tftp_server


FILES = [
    ("small_file", b"\x01small\x02"),
    ("large_file", b"a" * 1000),
    ("small_aligned_file", b"a" * 512),
    ("large_aligned_file", b"a" * 1024),
]
FILENAMES = [name for name, _ in FILES]


@pytest.fixture(params=FILES)
def file(request):
    return request.param


@pytest.fixture(params=FILENAMES)
def filename(request):
    return request.param


class TestingRouter(TftpRouter):
    def __init__(self):
        self.wrq_files = {filename: asyncio.Future() for filename in FILENAMES}
        self.rrq_files = {filename: (asyncio.Future(), bytestr)
                          for filename, bytestr in FILES}

    def rrq_recieved(self, packet, remote):
        if packet.filename not in self.rrq_files:
            raise RuntimeError("no such file '{}'".format(packet.filename))
        _, buffer = self.rrq_files[packet.filename]
        return io.BytesIO(buffer)

    def rrq_complete(self, filename, remote):
        future, _ = self.rrq_files[filename]
        future.set_result(True)

    def wrq_recieved(self, packet, remote):
        return io.BytesIO()

    def wrq_complete(self, buffer, filename, remote):
        self.wrq_files[filename].set_result(buffer)


@pytest.fixture(scope='session')
def loop():
    return asyncio.get_event_loop()


@pytest.fixture
def test_server(loop):
    listen = create_tftp_server(TestingRouter,
                                loop=loop,
                                local_addr=("127.0.0.1", 1069),
                                timeout=0.1)
    _, protocol = loop.run_until_complete(listen)
    return protocol


@pytest.fixture
def router(test_server):
    return test_server.router
