import asyncio

import pytest
from aiotftp.packet import create_packet, ErrorPacket, parse_packet
from aiotftp.parser import Mode, Opcode


class WriteClient(asyncio.DatagramProtocol):
    def __init__(self, filename, contents, loop):
        self.contents = contents
        self.filename = filename
        self.block_no = 0
        self._waiter = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport
        req = create_packet(
            Opcode.WRQ, filename=self.filename, mode=Mode.OCTET)
        transport.sendto(req.to_bytes(), ('127.0.0.1', 1069))

    def datagram_received(self, data, addr):
        try:
            packet = parse_packet(data)
            if isinstance(packet, ErrorPacket):
                raise RuntimeError(packet.error_msg)

            chunk, self.contents = self.contents[:512], self.contents[512:]
            payload = create_packet(
                Opcode.DATA, block_no=packet.block_no + 1, data=chunk)
            self.transport.sendto(payload.to_bytes(), addr)

            if len(chunk) < 512:
                self._waiter.set_result(None)
                self.transport.close()
        except Exception as exc:
            self._waiter.set_exception(exc)
            self.transport.close()

    async def wait(self):
        return await self._waiter


@pytest.mark.asyncio
async def test_write(filename, contents, server, event_loop):
    _, protocol = await event_loop.create_datagram_endpoint(
        lambda: WriteClient(filename, contents, event_loop),
        local_addr=('127.0.0.1', 0))

    await protocol.wait()
    assert await server.wrq_files[filename] == contents


@pytest.mark.asyncio
@pytest.mark.skip('Needs work')
async def test_write_notfound(server, event_loop):
    _, protocol = await event_loop.create_datagram_endpoint(
        lambda: WriteClient('notfound', b'', event_loop),
        local_addr=('127.0.0.1', 0))

    with pytest.raises(RuntimeError):
        assert await protocol.wait()
