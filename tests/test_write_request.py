import asyncio

import pytest
from aiotftp.packet import Data, Error, Mode, Opcode, parse, Request


class WriteClient(asyncio.DatagramProtocol):
    def __init__(self, filename, contents, loop):
        self.contents = contents
        self.filename = filename
        self.blockid = 0
        self._waiter = loop.create_future()

    def connection_made(self, transport):
        self.transport = transport
        try:
            req = Request(Opcode.WRQ, filename=self.filename, mode=Mode.OCTET)
            transport.sendto(bytes(req), ('127.0.0.1', 1069))
        except Exception as exc:
            self._waiter.set_exception(exc)
            self.transport.close()

    def datagram_received(self, data, addr):
        try:
            packet = parse(data)
            if isinstance(packet, Error):
                raise RuntimeError(packet.message)

            chunk, self.contents = self.contents[:512], self.contents[512:]
            payload = Data(blockid=packet.blockid + 1, data=chunk)
            self.transport.sendto(bytes(payload), addr)

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
async def test_write_notfound(server, event_loop):
    _, protocol = await event_loop.create_datagram_endpoint(
        lambda: WriteClient('notfound', b'', event_loop),
        local_addr=('127.0.0.1', 0))

    with pytest.raises(RuntimeError):
        assert await protocol.wait()
