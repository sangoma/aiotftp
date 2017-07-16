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


class SmallFile:
    name = "small_file"
    bytes = b"\x00\x01\x02\x03a small file\x04\x05\x06\x07"


class LargeFile:
    name = "large_file"
    bytes = (b"a" * 512) + b"z" * 128


@pytest.fixture(scope='session')
def loop():
    return asyncio.get_event_loop()


class ReadRouter(TftpRouter):
    def __init__(self, future):
        self.future = future

    @classmethod
    def with_future(cls):
        future = asyncio.Future()
        return cls(future), future

    def rrq_recieved(self, packet, remote):
        if packet.filename == SmallFile.name:
            return io.BytesIO(SmallFile.bytes)
        else:
            return io.BytesIO(LargeFile.bytes)

    def rrq_complete(self):
        self.future.set_result(True)


class ReadClient(asyncio.DatagramProtocol):
    def __init__(self, request):
        self.request = request
        self.recieved = io.BytesIO()
        self.acked = []

    def connection_made(self, transport):
        self.transport = transport
        transport.sendto(self.request.to_bytes(), ("127.0.0.1", 1069))

    def datagram_received(self, data, addr):
        pkt = parse_packet(data)
        if pkt.block_no not in self.acked:
            self.recieved.write(pkt.data)
        ack = create_packet(Opcode.ACK,
                            block_no=pkt.block_no)
        self.transport.sendto(ack.to_bytes(), addr)
        if len(pkt.data) < 512:
            self.transport.close()


@pytest.mark.parametrize("client,expected_bytes", [
    (ReadClient(create_packet(
        Opcode.RRQ, filename=SmallFile.name, mode=Mode.OCTET)),
        SmallFile.bytes),
    (ReadClient(create_packet(
        Opcode.RRQ, filename=LargeFile.name, mode=Mode.OCTET)),
        LargeFile.bytes),
])
def test_read_routing(client, expected_bytes, loop):
    router, future = ReadRouter.with_future()
    loop.run_until_complete(loop.create_datagram_endpoint(
        lambda: TftpProtocol(router),
        local_addr=("127.0.0.1", 1069)))
    loop.run_until_complete(loop.create_datagram_endpoint(
        lambda: client,
        local_addr=("127.0.0.1", 0)))
    loop.run_until_complete(future)
    recvd_bytes = client.recieved.getbuffer().tobytes()
    assert recvd_bytes == expected_bytes
