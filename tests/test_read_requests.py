import asyncio
import io
import pytest
import random
from aiotftp.mode import Mode
from aiotftp.opcode import Opcode
from aiotftp.packet import create_packet
from aiotftp.packet import parse_packet


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
            self.acked.append(pkt.block_no)
        ack = create_packet(Opcode.ACK,
                            block_no=pkt.block_no)
        self.transport.sendto(ack.to_bytes(), addr)
        if len(pkt.data) < 512:
            self.transport.close()


class DelayedAckClient(asyncio.DatagramProtocol):
    """Let each packet go unACKed at least twice before ACKing."""
    def __init__(self, request):
        self.request = request
        self.recieved = io.BytesIO()
        self.acked = []
        self.ack_next = []

    def connection_made(self, transport):
        self.transport = transport
        transport.sendto(self.request.to_bytes(), ("127.0.0.1", 1069))

    def datagram_received(self, data, addr):
        pkt = parse_packet(data)
        if pkt.block_no in self.acked:
            self.send_ack(pkt.block_no, addr)
        else:
            if pkt.block_no in self.ack_next:
                self.acked.append(pkt.block_no)
                self.send_ack(pkt.block_no, addr)
                self.recieved.write(pkt.data)
                if len(pkt.data) < 512:
                    self.transport.close()
            else:
                if random.choice(["ack next", "don't"]) == "ack next":
                    self.ack_next.append(pkt.block_no)

    def send_ack(self, block_no, addr):
        ack = create_packet(Opcode.ACK,
                            block_no=block_no)
        self.transport.sendto(ack.to_bytes(), addr)


@pytest.fixture(params=[ReadClient, DelayedAckClient])
def read_client(request):
    return request.param


@pytest.fixture
def read_request(filename, read_client, router, loop):
    """Perform each read request, returning received/expected bytes."""
    rrq = create_packet(Opcode.RRQ,
                        filename=filename,
                        mode=Mode.OCTET)
    _, rrq_client = loop.run_until_complete(loop.create_datagram_endpoint(
        lambda: read_client(rrq),
        local_addr=("127.0.0.1", 0)))
    future, expected = router.rrq_files[filename]
    loop.run_until_complete(future)
    return rrq_client.recieved.getbuffer().tobytes(), expected


def test_read_routing(read_request, loop):
    recieved, expected = read_request
    assert recieved == expected
