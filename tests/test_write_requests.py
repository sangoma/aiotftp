import asyncio
import pytest
import io
from aiotftp import TftpRouter
from aiotftp import TftpProtocol
from aiotftp.error_code import ErrorCode
from aiotftp.mode import Mode
from aiotftp.opcode import Opcode
from aiotftp.packet import create_packet
from aiotftp.packet import parse_packet


class WriteRouter(TftpRouter):
    def __init__(self, future):
        self.future = future

    @classmethod
    def with_future(cls):
        future = asyncio.Future()
        return cls(future), future

    def wrq_recieved(self, packet, remote):
        return io.BytesIO()

    def wrq_complete(self, buf):
        self.future.set_result(buf)


class WriteClient(asyncio.DatagramProtocol):
    def __init__(self, file):
        self.file = file
        self.block_no = 0

    def connection_made(self, transport):
        self.transport = transport
        req = create_packet(Opcode.WRQ, filename="test", mode=Mode.OCTET)
        transport.sendto(req.to_bytes(), ("127.0.0.1", 1069))

    def datagram_received(self, data, addr):
        packet = parse_packet(data)
        payload = create_packet(Opcode.DATA,
                                block_no=packet.block_no+1,
                                data=self.file.read(512)).to_bytes()
        self.transport.sendto(payload, addr)
        if len(payload.data) < 512:
            self.transport.close()


@pytest.mark.parametrize("buffer", [
        io.BytesIO(b"small file"),
        io.BytesIO(b"large file" * 60),
])
def test_write_routing(buffer, loop):
    client = WriteClient(buffer)
    router, future = WriteRouter.with_future()

    loop.run_until_complete(loop.create_datagram_endpoint(
        lambda: TftpProtocol(router),
        local_addr=("127.0.0.1", 1069)))
    loop.run_until_complete(loop.create_datagram_endpoint(
        lambda: client,
        local_addr=("127.0.0.1", 0)))
    loop.run_until_complete(future)

    client_buf = buffer.getbuffer().tobytes()
    written_buf = future.result().getbuffer().tobytes()
    assert client_buf == written_buf
