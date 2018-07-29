import enum
import attr


def ushort(n):
    return int.to_bytes(n, length=2, byteorder='big')


def parse_ushort(buf):
    if len(buf) != 2:
        raise ValueError("Requires two bytes")
    return int.from_bytes(buf, byteorder='big')


def pairwise(data):
    it = iter(data)
    return dict(zip(it, it))


class Opcode(enum.Enum):
    RRQ = ushort(1)
    WRQ = ushort(2)
    DATA = ushort(3)
    ACK = ushort(4)
    ERROR = ushort(5)

    @property
    def is_request(self):
        return self in (Opcode.RRQ, Opcode.WRQ)


class Mode(enum.Enum):
    NETASCII = b'netascii'
    OCTET = b'octet'
    MAIL = b'mail'

    @classmethod
    def get(cls, s):
        return cls(s.lower())


class ErrorCode(enum.Enum):
    NOTDEFINED = ushort(0)
    FILENOTFOUND = ushort(1)
    ACCESSVIOLATION = ushort(2)
    DISKFULL = ushort(3)
    ILLEGALOPERATION = ushort(4)
    UNKNOWNID = ushort(5)
    FILEEXISTS = ushort(6)
    NOSUCHUSER = ushort(7)


class Packet:
    @property
    def is_request(self):
        return self.opcode.is_request


@attr.s
class Request(Packet):
    opcode = attr.ib()
    filename = attr.ib()
    mode = attr.ib()
    options = attr.ib(factory=dict)

    @classmethod
    def parse(cls, buf):
        filename, mode, *extensions, _ = buf[2:].tobytes().split(b'\x00')
        return cls(
            opcode=Opcode(buf[0:2]),
            filename=filename.decode('ascii'),
            mode=Mode.get(mode),
            options=pairwise(field.decode('ascii') for field in extensions))

    def __bytes__(self):
        return b''.join((self.opcode.value, bytes(self.filename, "ascii"),
                         b"\x00", self.mode.value, b"\x00"))


@attr.s
class Data(Packet):
    opcode = Opcode.DATA

    block_no = attr.ib()
    data = attr.ib()

    @classmethod
    def parse(cls, buf):
        return cls(block_no=parse_ushort(buf[2:4]), data=buf[4:])

    def __bytes__(self):
        return b''.join((self.opcode.value, ushort(self.block_no), self.data))


@attr.s
class Ack(Packet):
    opcode = Opcode.ACK

    block_no = attr.ib()

    @classmethod
    def parse(cls, buf):
        return cls(block_no=parse_ushort(buf[2:4]))

    def __bytes__(self):
        return b''.join((self.opcode.value, ushort(self.block_no)))


@attr.s
class Error(Packet):
    opcode = Opcode.ERROR

    code = attr.ib()
    message = attr.ib()

    @classmethod
    def parse(cls, buf):
        message, _ = buf[4:].tobytes().split(b'\x00')
        return cls(code=ErrorCode(buf[2:4]), message=message.decode('ascii'))

    def __bytes__(self):
        return b''.join((self.opcode.value, self.code.value,
                         bytes(self.message, "ascii"), b"\x00"))


PACKETS = {
    Opcode.RRQ: Request,
    Opcode.WRQ: Request,
    Opcode.DATA: Data,
    Opcode.ACK: Ack,
    Opcode.ERROR: Error,
}


def parse(data):
    """Return a Packet class appropriate to what's in the buffer."""
    with memoryview(data) as buf:
        opcode = Opcode(buf[0:2])
        try:
            return PACKETS[opcode].parse(buf)
        except KeyError:
            raise ValueError("Invalid TFTP packet")
