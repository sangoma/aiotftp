import asyncio
import random

from aiotftp.packet import Ack, Mode, Opcode, parse, Request
import pytest


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
        transport.sendto(bytes(self.request), ('127.0.0.1', 1069))

    def datagram_received(self, data, addr):
        try:
            packet = parse(data)
            if packet.blockid in self.acked:
                self.send_ack(packet.blockid, addr)
            else:
                if packet.blockid in self.ack_next:
                    self.acked.append(packet.blockid)
                    self.send_ack(packet.blockid, addr)
                    self.received.extend(packet.data)
                    if len(packet.data) < 512:
                        self._waiter.set_result(self.received)
                        self.transport.close()
                else:
                    if random.choice(["ack next", "don't"]) == "ack next":
                        self.ack_next.append(packet.blockid)
        except Exception as exc:
            self._waiter.set_exception(exc)
            self.transport.close()

    def send_ack(self, blockid, addr):
        ack = Ack(blockid)
        self.transport.sendto(bytes(ack), addr)

    async def wait(self):
        return await self._waiter


@pytest.mark.asyncio
async def test_read_delayed(filename, contents, server, event_loop):
    rrq = Request(Opcode.RRQ, filename=filename, mode=Mode.OCTET)
    _, protocol = await event_loop.create_datagram_endpoint(
        lambda: DelayedAckClient(rrq, event_loop), local_addr=('127.0.0.1', 0))

    assert await protocol.wait() == contents
