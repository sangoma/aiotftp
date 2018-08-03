import asyncio
import logging

from .helpers import get_tid, set_exception, set_result
from .packet import Ack, Data, Error, Mode, Opcode, Request, parse

LOG = logging.getLogger(__name__)


class InboundDataProtocol(asyncio.DatagramProtocol):
    def __init__(self, stream, *, tid, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._timeout = 2.0

        self.stream = stream
        self.tid = tid
        self.blockid = 1
        self.ack_handler = None

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        if exc:
            return self.stream.set_exception(exc)
        return self.stream.feed_eof()

    def datagram_received(self, data, addr):
        tid = get_tid(addr)
        if not self.tid:
            self.tid = tid
        elif self.tid != tid:
            LOG.debug('Unsolicited packet from {}'.format(addr))
            return

        packet = parse(data)
        if isinstance(packet, Error):
            self.stream.set_exception(FileNotFoundError(packet.message))

        elif isinstance(packet, Data) and packet.blockid == self.blockid:
            last = len(packet.data) < 512

            self.ack(self.blockid, last)
            self.stream.feed_data(packet.data)
            if last:
                self.stream.feed_eof()

            self.blockid += 1
            if self.blockid > 65535:
                self.blockid = 0

    def ack(self, blockid, last):
        if self.ack_handler:
            self.ack_handler.cancel()
            self.ack_handler = None

        packet = bytes(Ack(blockid))
        if last:
            return self.transport.sendto(packet, self.tid)

        async def transmission_loop():
            while True:
                self.transport.sendto(packet, self.tid)
                await asyncio.sleep(self._timeout)

        self.ack_handler = self._loop.create_task(transmission_loop())

    def start(self):
        self.ack(0, False)


class OutboundDataProtocol(asyncio.DatagramProtocol):
    def __init__(self, *, tid, timeout=None, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._timeout = 2.0
        self._waiter = None

        self.tid = tid
        self.blockid = 0
        self.ack_handler = None
        self.output_size = 0

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        tid = get_tid(addr)
        if not self.tid:
            self.tid = tid
        elif self.tid != tid:
            LOG.debug('Unsolicited packet from {}'.format(addr))
            return

        packet = parse(data)
        if isinstance(packet, Error):
            waiter = self._waiter
            if waiter is not None:
                self._waiter = None
                set_exception(waiter, RuntimeError(packet.message))

        elif isinstance(packet, Ack) and packet.blockid == self.blockid:
            waiter = self._waiter
            if waiter is not None:
                self._waiter = None
                set_result(waiter, False)

    async def write(self, chunk) -> None:
        self.blockid += 1
        if self.blockid > 65535:
            self.blockid = 0

        packet = bytes(Data(blockid=self.blockid, data=chunk))

        async def sendto_forever():
            self.output_size += len(chunk)
            while True:
                self.transport.sendto(packet, self.tid)
                await asyncio.sleep(self._timeout)

        try:
            coro = asyncio.ensure_future(sendto_forever())
            await self._wait('write')
        finally:
            coro.cancel()

        if len(chunk) < 512:
            self.transport.close()

    async def start(self, filename, remote_addr):
        req = Request(Opcode.WRQ, filename=filename, mode=Mode.OCTET)
        self.transport.sendto(bytes(req), remote_addr)
        await self._wait('start')

    async def _wait(self, func_name):
        if self._waiter is not None:
            raise RuntimeError(
                '{} called while another coroutine is '
                'already waiting for incoming data'.format(func_name))

        waiter = self._waiter = self._loop.create_future()
        try:
            await waiter
        finally:
            self._waiter = None
