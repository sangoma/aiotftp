import asyncio
import io
import pytest
import random
from aiotftp.mode import Mode
from aiotftp.opcode import Opcode
from aiotftp.packet import create_packet
from aiotftp.packet import parse_packet


class WriteClient(asyncio.DatagramProtocol):
    def __init__(self, filename, file):
        self.file = file
        self.filename = filename
        self.block_no = 0

    def connection_made(self, transport):
        self.transport = transport
        req = create_packet(Opcode.WRQ,
                            filename=self.filename,
                            mode=Mode.OCTET)
        transport.sendto(req.to_bytes(), ("127.0.0.1", 1069))

    def datagram_received(self, data, addr):
        packet = parse_packet(data)
        payload = create_packet(Opcode.DATA,
                                block_no=packet.block_no+1,
                                data=self.file.read(512)).to_bytes()
        self.transport.sendto(payload, addr)
        if len(payload.data) < 512:
            self.transport.close()


@pytest.fixture
def write_request(file, router, loop):
    """Perform each write request, returning received/expected bytes."""
    filename, filebytes = file
    _, wrq_client = loop.run_until_complete(loop.create_datagram_endpoint(
        lambda: WriteClient(filename, io.BytesIO(filebytes)),
        local_addr=("127.0.0.1", 0)))
    future = router.wrq_files[filename]
    loop.run_until_complete(future)
    return future.result().getbuffer().tobytes(), filebytes


def test_write_routing(write_request, loop):
    received, expected = write_request
    assert received == expected
