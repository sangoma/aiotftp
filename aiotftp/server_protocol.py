import asyncio
from aiotftp import TftpRouter
from aiotftp.error_code import ErrorCode
from aiotftp.mode import Mode
from aiotftp.opcode import Opcode
from aiotftp.packet import ErrorPacket
from aiotftp.packet import create_packet
from aiotftp.packet import parse_packet
from aiotftp.read_protocol import TftpReadProtocol
from aiotftp.write_protocol import TftpWriteProtocol


class TftpProtocol(asyncio.DatagramProtocol):
    """Primary listener to dispatch incoming requests."""
    def __init__(self, router: TftpRouter):

        self.router = router
        self.loop = asyncio.get_event_loop()

        opcode_err = create_packet(Opcode.ERROR,
                                   error_code=ErrorCode.NOTDEFINED,
                                   error_msg="invalid opcode")
        self.opcode_err = opcode_err.to_bytes()
        mode_err = create_packet(Opcode.ERROR,
                                 error_code=ErrorCode.NOTDEFINED,
                                 error_msg="OCTET mode only")
        self.mode_err = mode_err.to_bytes()

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, buffer, remote):
        packet = parse_packet(buffer)
        if not packet.is_request():
            self.transport.sendto(self.opcode_err, remote)
            return
        elif packet.mode != Mode.OCTET:
            self.transport.sendto(self.mode_err, remote)
            return

        self.dispatch(packet, remote)

    def dispatch(self, packet, remote):
        handler = None

        if packet.opcode == Opcode.RRQ:
            iobuf = self.router.rrq_recieved(packet, remote)
            if isinstance(iobuf, ErrorPacket):
                self.transport.sendto(iobuf.to_bytes(), remote)
            else:
                def handler():
                    callback = getattr(self.router.rrq_complete, None)
                    return TftpReadProtocol(remote,
                                            iobuf,
                                            callback)
        else:
            iobuf = self.router.wrq_recieved(packet, remote)
            if isinstance(iobuf, ErrorPacket):
                self.transport.sendto(iobuf.to_bytes(), remote)
            else:
                def handler():
                    callback = getattr(self.router.wrq_complete, None)
                    return TftpWriteProtocol(remote,
                                             iobuf,
                                             callback)

        if handler:
            connect = self.loop.create_datagram_endpoint(
                handler, local_addr=("0.0.0.0", 0))
            self.loop.create_task(connect)
