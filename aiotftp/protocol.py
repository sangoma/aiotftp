import asyncio
import logging
import traceback
from contextlib import suppress

import async_timeout
import attr

from .helpers import set_result
from .logger import AccessLogger, access_log
from .packet import Ack, Error, Data, ErrorCode, Mode, Opcode, parse
from .transfers import StreamReader

LOG = logging.getLogger(__name__)

OPCODE_ERR = bytes(Error(ErrorCode.NOTDEFINED, message="invalid opcode"))
MODE_ERR = bytes(Error(ErrorCode.NOTDEFINED, message="OCTET mode only"))


@attr.s
class Request:
    method = attr.ib()
    filename = attr.ib()
    remote = attr.ib()


class RequestHandler(asyncio.DatagramProtocol):
    """Primary listener to dispatch incoming requests."""

    def __init__(self,
                 read,
                 write,
                 *,
                 loop=None,
                 timeout=2.0,
                 access_log_class=AccessLogger,
                 access_log=access_log,
                 access_log_format=AccessLogger.LOG_FORMAT) -> None:
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._timeout = timeout
        self._task_handler = None

        self.read = read
        self.write = write

        self.access_log = access_log
        if access_log:
            self.access_logger = access_log_class(access_log,
                                                  access_log_format)
        else:
            self.access_logger = None

    def connection_made(self, transport):
        self.transport = transport

    def connection_lost(self, exc):
        if self._task_handler is not None:
            self._task_handler.cancel()
        self._task_handler = None

    def datagram_received(self, data, addr):
        packet = parse(data)
        if not packet.is_request:
            self.transport.sendto(OPCODE_ERR)
        elif packet.mode != Mode.OCTET:
            self.transport.sendto(MODE_ERR)
        else:
            self._task_handler = self._loop.create_task(
                self.start(packet, addr))

    def send(self, packet, addr=None):
        self.transport.sendto(packet, addr)

    async def start(self, packet, addr):
        request = Request(
            filename=packet.filename, remote=addr, method=packet.opcode)

        if self.access_log:
            now = self._loop.time()

        if packet.opcode == Opcode.RRQ:
            try:
                response = await self.read(request)
            except Exception:
                formatted_lines = traceback.format_exc().splitlines()
                packet = Error(
                    ErrorCode.NOTDEFINED, message=formatted_lines[-1])
                self.transport.sendto(bytes(packet), addr)
            else:
                transport, protocol = await self._loop.create_datagram_endpoint(
                    lambda: ReadRequestHandler(timeout=self._timeout, loop=self._loop),
                    remote_addr=addr[:2])
                try:
                    await response.start(protocol)
                    if self.access_log:
                        self.log_access(request, response,
                                        self._loop.time() - now)
                except FileNotFoundError:
                    packet = Error(ErrorCode.FILENOTFOUND, message="not found")
                    self.transport.sendto(bytes(packet), addr)
                finally:
                    transport.close()

        elif packet.opcode == Opcode.WRQ:
            transfer = StreamReader(loop=self._loop)
            transport, protocol = await self._loop.create_datagram_endpoint(
                lambda: WriteRequestHandler(transfer, timeout=self._timeout, loop=self._loop),
                remote_addr=addr[:2])
            try:
                await self.write(request, transfer)
                if self.access_log:
                    self.log_access(request, None, self._loop.time() - now)
            except Exception:
                LOG.exception("Inbound transfer crashed")
            finally:
                transport.close()

    async def shutdown(self, timeout=15.0):
        with suppress(asyncio.CancelledError, asyncio.TimeoutError):
            with async_timeout.timeout(timeout, loop=self._loop):
                if (self._task_handler is not None
                        and not self._task_handler.done()):
                    await self._task_handler

        if self._task_handler is not None:
            self._task_handler.cancel()

        if self.transport is not None:
            self.transport.close()
            self.transport = None

    def log_access(self, request, response, time):
        if self.access_logger is not None:
            self.access_logger.log(request, response, time)


class ReadRequestHandler(asyncio.DatagramProtocol):
    def __init__(self, *, timeout=2.0, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._timeout = timeout

        self.counter = 0
        self._waiter = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        packet = parse(data)
        if packet.opcode == Opcode.ACK and packet.block_no == self.counter:
            waiter = self._waiter
            if waiter is not None:
                self._waiter = None
                set_result(waiter, False)

    async def write(self, chunk) -> None:
        self.counter += 1
        if self.counter > 65535:
            self.counter = 0

        packet = bytes(Data(block_no=self.counter, data=chunk))

        async def sendto_forever():
            while True:
                self.transport.sendto(packet)
                await asyncio.sleep(self._timeout)

        try:
            coro = asyncio.ensure_future(sendto_forever())
            await self._wait('write')
        finally:
            coro.cancel()

        if len(chunk) < 512:
            self.transport.close()

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


class WriteRequestHandler(asyncio.DatagramProtocol):
    def __init__(self, stream, *, timeout=2.0, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._timeout = timeout

        self.counter = 0
        self.stream = stream
        self.ack_handler = None

    def connection_made(self, transport):
        self.transport = transport
        self.ack(False)

    def connection_lost(self, exc):
        if exc:
            return self.stream.set_exception(exc)
        return self.stream.feed_eof()

    def datagram_received(self, data, addr):
        packet = parse(data)
        if packet.opcode == Opcode.DATA and packet.block_no == self.counter:
            last = len(packet.data) < 512

            self.ack(last)
            self.stream.feed_data(packet.data)
            if last:
                self.stream.feed_eof()

    def ack(self, last):
        if self.ack_handler:
            self.ack_handler.cancel()
            self.ack_handler = None

        packet = bytes(Ack(block_no=self.counter))
        if last:
            return self.transport.sendto(packet)

        async def transmission_loop():
            while True:
                self.transport.sendto(packet)
                await asyncio.sleep(self._timeout)

        self.counter += 1
        if self.counter > 65535:
            self.counter = 0
        self.ack_handler = self._loop.create_task(transmission_loop())
