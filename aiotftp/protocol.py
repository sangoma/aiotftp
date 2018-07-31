import asyncio
import logging
import traceback
from contextlib import suppress

import async_timeout
import attr

from .helpers import get_tid, set_result
from .logger import AccessLogger, access_log
from .packet import Ack, Error, Data, ErrorCode, Mode, Opcode, parse
from .streams import StreamReader

LOG = logging.getLogger(__name__)

OPCODE_ERR = bytes(Error(ErrorCode.NOTDEFINED, message="invalid opcode"))
MODE_ERR = bytes(Error(ErrorCode.NOTDEFINED, message="OCTET mode only"))


@attr.s
class Request:
    chunk_size = 512

    tid = attr.ib()
    method = attr.ib()
    filename = attr.ib()
    remote = attr.ib()


class RequestHandler(asyncio.DatagramProtocol):
    """Primary listener to dispatch incoming requests."""

    def __init__(self, read, write, *,
                 loop=None,
                 timeout=None,
                 access_log_class=AccessLogger,
                 access_log=access_log,
                 access_log_format=AccessLogger.LOG_FORMAT) -> None:
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._timeout = timeout or 2.0
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
        tid = get_tid(addr)
        request = Request(
            filename=packet.filename,
            remote=addr,
            method=packet.opcode,
            tid=tid)

        if packet.opcode == Opcode.RRQ:
            await self._start_rrq(request, packet, tid)

        elif packet.opcode == Opcode.WRQ:
            await self._start_wrq(request, packet, tid)

    async def _start_rrq(self, request, packet, tid):
        if self.access_log:
            now = self._loop.time()

        if self.read is None:
            packet = Error(
                ErrorCode.ACCESSVIOLATION, message="Permission denied")
            self.transport.sendto(bytes(packet), tid)
            return

        try:
            response = await self.read(request)
        except Exception:
            formatted_lines = traceback.format_exc().splitlines()
            packet = Error(ErrorCode.NOTDEFINED, message=formatted_lines[-1])
            self.transport.sendto(bytes(packet), tid)
            return

        try:
            await response.prepare(request)
        except FileNotFoundError:
            packet = Error(ErrorCode.FILENOTFOUND, message="File not found")
            self.transport.sendto(bytes(packet), tid)
        finally:
            await response.write_eof()

        if self.access_log:
            self.log_access(request, response, self._loop.time() - now)

    async def _start_wrq(self, request, packet, tid):
        if self.access_log:
            now = self._loop.time()

        if self.write is None:
            packet = Error(
                ErrorCode.ACCESSVIOLATION, message="Permission denied")
            self.transport.sendto(bytes(packet), tid)
            return

        transfer = StreamReader(loop=self._loop)
        transport, protocol = await self._loop.create_datagram_endpoint(
            lambda: RequestStreamHandler(transfer, tid=tid, timeout=self._timeout, loop=self._loop),
            remote_addr=tid)
        try:
            protocol.start()
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


class RequestStreamHandler(asyncio.DatagramProtocol):
    def __init__(self, stream, *, tid=None, timeout=None, loop=None):
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
        self._timeout = timeout or 2.0

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
        if packet.opcode == Opcode.ERROR:
            self.stream.set_exception(FileNotFoundError(packet.message))
        elif packet.opcode == Opcode.DATA and packet.block_no == self.blockid:
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
