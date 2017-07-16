from aiotftp import AioTftpError
from aiotftp import PacketError
from aiotftp.error_code import ErrorCode
from aiotftp.mode import Mode
from aiotftp.opcode import Opcode
from aiotftp.short_int import ShortInt


def create_packet(opcode: Opcode,
                  *,
                  filename: str=None,
                  mode: Mode=None,
                  block_no: int=None,
                  data: bytes=None,
                  error_code: ErrorCode=None,
                  error_msg: str=None):
    """Create a Packet instance appropriate to the passed arguments.

    This convenience function is honestly quite messy, but more
    ergonomic than trying to work with all the sub-classes of the
    Packet type directly.
    """
    def must_have(lcls, *args):
        for arg in args:
            if lcls[arg] is None:
                raise AioTftpError("missing parameters for {}".format(opcode))

    if opcode.is_request():
        must_have(locals(), "filename", "mode")
        return RequestPacket(opcode, filename, mode)
    elif opcode == Opcode.DATA:
        must_have(locals(), "block_no", "data")
        return DataPacket(block_no, data)
    elif opcode == Opcode.ACK:
        must_have(locals(), "block_no")
        return AckPacket(block_no)
    elif opcode == Opcode.ERROR:
        must_have(locals(), "error_code", "error_msg")
        return ErrorPacket(error_code, error_msg)


def parse_packet(buf):
    """Return a Packet class appropriate to what's in the buffer."""
    map = [
        (Opcode.RRQ, RequestPacket),
        (Opcode.WRQ, RequestPacket),
        (Opcode.DATA, DataPacket),
        (Opcode.ACK, AckPacket),
        (Opcode.ERROR, ErrorPacket),
    ]

    buf_opcode = Opcode.from_bytes(buf[0:2])
    for map_opcode, cls in map:
        if buf_opcode == map_opcode:
            return cls.from_bytes(buf)
    raise PacketError("buffer does not contain valid TFTP packet")


def extract_cstring(bytes):
    """Return an ascii string up to the first null byte."""
    s, null, _ = bytes.partition(b'\x00')
    return s.decode("ascii")


class Packet:
    def is_request(self):
        return self.opcode.is_request()


class RequestPacket(Packet):
    def __init__(self, opcode, filename, mode):
        self.opcode = opcode
        self.filename = filename
        self.mode = mode

    @classmethod
    def from_bytes(cls, buf):
        opcode = Opcode.from_bytes(buf[0:2])
        filename = extract_cstring(buf[2:])
        mode_offset = 2 + len(filename) + 1
        mode = Mode.from_string(extract_cstring(buf[mode_offset:]))
        return cls(opcode, filename, mode)

    def to_bytes(self):
        return (self.opcode.to_bytes() +
                bytes(self.filename, "ascii") +
                b"\x00" +
                self.mode.to_bytes() +
                b"\x00")


class DataPacket(Packet):
    def __init__(self, block_no, data):
        self.opcode = Opcode.DATA
        self.block_no = block_no
        self.data = data

    @classmethod
    def from_bytes(cls, buf):
        block_no = ShortInt.from_bytes(buf[2:4])
        data = buf[4:]
        return cls(block_no, data)

    def to_bytes(self):
        return (self.opcode.to_bytes() +
                ShortInt(self.block_no).to_bytes() +
                self.data)


class AckPacket(Packet):
    def __init__(self, block_no):
        self.opcode = Opcode.ACK
        self.block_no = block_no

    @classmethod
    def from_bytes(cls, buf):
        block_no = ShortInt.from_bytes(buf[2:4])
        return cls(block_no)

    def to_bytes(self):
        return self.opcode.to_bytes() + ShortInt(self.block_no).to_bytes()


class ErrorPacket(Packet):
    def __init__(self, error_code, error_msg):
        self.opcode = Opcode.ERROR
        self.error_code = error_code
        self.error_msg = error_msg

    @classmethod
    def from_bytes(cls, buf):
        error_code = ErrorCode.from_bytes(buf[2:4])
        error_msg = extract_cstring(buf[4:])
        return cls(error_code, error_msg)

    def to_bytes(self):
        return (self.opcode.to_bytes() +
                self.error_code.to_bytes() +
                bytes(self.error_msg, "ascii") +
                b"\x00")
