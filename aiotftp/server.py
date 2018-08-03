import asyncio
import logging
import traceback
from contextlib import suppress

import async_timeout
import attr

from .helpers import get_tid
from .logger import AccessLogger, access_log
from .protocol import InboundDataProtocol
from .packet import Error, ErrorCode, Mode, Opcode, parse
from .streams import StreamReader

LOG = logging.getLogger(__name__)

OPCODE_ERR = bytes(Error(ErrorCode.NOTDEFINED, message="invalid opcode"))
MODE_ERR = bytes(Error(ErrorCode.NOTDEFINED, message="OCTET mode only"))


@attr.s
class Request:
    chunk_size = 512
    timeout = 2.0

    tid = attr.ib()
    method = attr.ib()
    filename = attr.ib()
    remote = attr.ib()

    _loop = attr.ib()

    @_loop.default
    def _get_event_loop(self):
        return asyncio.get_event_loop()

    async def accept(self):
        transfer = StreamReader(loop=self._loop)
        transport, protocol = await self._loop.create_datagram_endpoint(
            lambda: InboundDataProtocol(transfer, tid=self.tid, loop=self._loop),
            remote_addr=self.tid)

        protocol.start()
        return transfer

    async def read(self):
        payload = bytearray()
        async for chunk in await self.accept():
            payload.extend(chunk)
        return bytes(payload)


class RequestHandler(asyncio.DatagramProtocol):
    """Primary listener to dispatch incoming requests."""

    def __init__(self, read, write, *,
                 loop=None,
                 access_log_class=AccessLogger,
                 access_log=access_log,
                 access_log_format=AccessLogger.LOG_FORMAT) -> None:
        if loop is None:
            loop = asyncio.get_event_loop()
        self._loop = loop
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
            LOG.exception("RRQ failed")
            formatted_lines = traceback.format_exc().splitlines()
            packet = Error(ErrorCode.NOTDEFINED, message=formatted_lines[-1])
            self.transport.sendto(bytes(packet), tid)
            return

        try:
            await response.prepare(request)
        except FileNotFoundError:
            packet = Error(ErrorCode.FILENOTFOUND, message="File not found")
            self.transport.sendto(bytes(packet), tid)
            return
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

        try:
            await self.write(request)
        except Exception:
            LOG.exception("WWQ failed")
            formatted_lines = traceback.format_exc().splitlines()
            packet = Error(ErrorCode.NOTDEFINED, message=formatted_lines[-1])
            self.transport.sendto(bytes(packet), tid)
            return
        except FileNotFoundError:
            packet = Error(ErrorCode.FILENOTFOUND, message="File not found")
            self.transport.sendto(bytes(packet), tid)
            return

        if self.access_log:
            self.log_access(request, None, self._loop.time() - now)

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
