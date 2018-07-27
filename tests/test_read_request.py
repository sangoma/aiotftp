import asyncio
import random

from aiotftp.packet import create_packet, ErrorPacket, parse_packet
from aiotftp.parser import Mode, Opcode
import pytest


class ReadClient(asyncio.DatagramProtocol):
    def __init__(self, request, loop):
        self.request = request
        self.received = bytearray()
        self.acked = []
        self._waiter = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport
        transport.sendto(self.request.to_bytes(), ('127.0.0.1', 1069))

    def datagram_received(self, data, addr):
        try:
            packet = parse_packet(data)
            if isinstance(packet, ErrorPacket):
                raise RuntimeError(packet.error_msg)

            if packet.block_no not in self.acked:
                self.received.extend(packet.data)
                self.acked.append(packet.block_no)

            self.send_ack(packet.block_no, addr)
            if len(packet.data) < 512:
                self.transport.close()
                self._waiter.set_result(self.received)
        except Exception as exc:
            self._waiter.set_exception(exc)
            self.transport.close()

    def send_ack(self, block_no, addr):
        ack = create_packet(Opcode.ACK, block_no=block_no)
        self.transport.sendto(ack.to_bytes(), addr)

    async def wait(self):
        return await self._waiter


class DelayedAckClient(asyncio.DatagramProtocol):
    """Let each packet go unACKed at least twice before ACKing."""

    def __init__(self, request, loop):
        self.request = request
        self.received = bytearray()
        self.acked = []
        self.ack_next = []
        self._waiter = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport
        transport.sendto(self.request.to_bytes(), ('127.0.0.1', 1069))

    def datagram_received(self, data, addr):
        try:
            packet = parse_packet(data)
            if packet.block_no in self.acked:
                self.send_ack(packet.block_no, addr)
            else:
                if packet.block_no in self.ack_next:
                    self.acked.append(packet.block_no)
                    self.send_ack(packet.block_no, addr)
                    self.received.extend(packet.data)
                    if len(packet.data) < 512:
                        self._waiter.set_result(self.received)
                        self.transport.close()
                else:
                    if random.choice(["ack next", "don't"]) == "ack next":
                        self.ack_next.append(packet.block_no)
        except Exception as exc:
            self._waiter.set_exception(exc)
            self.transport.close()

    def send_ack(self, block_no, addr):
        ack = create_packet(Opcode.ACK, block_no=block_no)
        self.transport.sendto(ack.to_bytes(), addr)

    async def wait(self):
        return await self._waiter


@pytest.fixture(params=[ReadClient, DelayedAckClient])
def read_client(request, event_loop):
    return request.param


@pytest.mark.asyncio
async def test_read(filename, contents, read_client, server, event_loop):
    rrq = create_packet(Opcode.RRQ, filename=filename, mode=Mode.OCTET)
    _, protocol = await event_loop.create_datagram_endpoint(
        lambda: read_client(rrq, event_loop), local_addr=('127.0.0.1', 0))

    assert await protocol.wait() == contents


@pytest.mark.asyncio
async def test_read_notfound(server, event_loop):
    rrq = create_packet(Opcode.RRQ, filename='notfound', mode=Mode.OCTET)
    _, protocol = await event_loop.create_datagram_endpoint(
        lambda: ReadClient(rrq, event_loop), local_addr=('127.0.0.1', 0))

    with pytest.raises(RuntimeError):
        assert await protocol.wait()
