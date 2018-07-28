import enum


def short(n):
    return int.to_bytes(n, length=2, byteorder='big')


def parse_short(buf):
    return int.from_bytes(buf, byteorder='big')


def pairwise(data):
    it = iter(data)
    return dict(zip(it, it))


class Opcode(enum.Enum):
    RRQ = short(1)
    WRQ = short(2)
    DATA = short(3)
    ACK = short(4)
    ERROR = short(5)

    @property
    def is_request(self):
        return self in (Opcode.RRQ, Opcode.WRQ)


class Mode(enum.Enum):
    NETASCII = "netascii"
    OCTET = "octet"
    MAIL = "mail"

    @classmethod
    def get(cls, s):
        return cls(s.lower())


class ErrorCode(enum.Enum):
    NOTDEFINED = short(0)
    FILENOTFOUND = short(1)
    ACCESSVIOLATION = short(2)
    DISKFULL = short(3)
    ILLEGALOPERATION = short(4)
    UNKNOWNID = short(5)
    FILEEXISTS = short(6)
    NOSUCHUSER = short(7)


class Packet:
    @property
    def is_request(self):
        return self.opcode.is_request


class Request(Packet):
    def __init__(self, opcode, filename, mode, options):
        self.opcode = opcode
        self.filename = filename
        self.mode = mode
        self.options = {}

    @classmethod
    def parse(cls, buf):
        filename, mode, *extensions, _ = buf[2:].tobytes().split(b'\x00')
        return cls(
            opcode=Opcode(buf[0:2]),
            filename=filename.decode('ascii'),
            mode=Mode.get(mode.decode('ascii')),
            options=pairwise(field.decode('ascii') for field in extensions))

    def __bytes__(self):
        return b''.join((self.opcode, bytes(self.filename, "ascii"), b"\x00",
                         self.mode.value, b"\x00"))


class Data(Packet):
    opcode = Opcode.DATA

    def __init__(self, block_no, data):
        self.block_no = block_no
        self.data = data

    @classmethod
    def parse(cls, buf):
        return cls(block_no=parse_short(buf[2:4]), data=buf[4:])

    def __bytes__(self):
        return b''.join((self.opcode.value + short(self.block_no), self.data))


class Ack(Packet):
    opcode = Opcode.ACK

    def __init__(self, block_no):
        self.block_no = block_no

    @classmethod
    def parse(cls, buf):
        return cls(block_no=parse_short(buf[2:4]))

    def __bytes__(self):
        return b''.join((self.opcode.value, short(self.block_no)))


class Error(Packet):
    opcode = Opcode.ERROR

    def __init__(self, code, message):
        self.code = code
        self.message = message

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
