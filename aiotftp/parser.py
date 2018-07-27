import enum


class ShortInt(int):
    """Convenience class for the often-used short int."""

    @classmethod
    def from_bytes(self, buf):
        if len(buf) != 2:
            raise ValueError("ShortInt requires exactly 2 "
                             "bytes, {} received".format(len(buf)))
        return int.from_bytes(buf, byteorder="big")

    def to_bytes(self):
        return int.to_bytes(self, length=2, byteorder="big")


class Opcode(enum.Enum):
    RRQ = ShortInt(1)
    WRQ = ShortInt(2)
    DATA = ShortInt(3)
    ACK = ShortInt(4)
    ERROR = ShortInt(5)

    @classmethod
    def from_bytes(cls, buf):
        return cls(ShortInt.from_bytes(buf))

    def is_request(self):
        return self in (Opcode.RRQ, Opcode.WRQ)

    def to_bytes(self):
        return self.value.to_bytes()


class Mode(enum.Enum):
    NETASCII = "netascii"
    OCTET = "octet"
    MAIL = "mail"

    @classmethod
    def from_string(cls, s):
        return cls(s.lower())

    def to_bytes(self):
        return bytes(self.value, encoding="ascii")


class ErrorCode(enum.Enum):
    NOTDEFINED = ShortInt(0)
    FILENOTFOUND = ShortInt(1)
    ACCESSVIOLATION = ShortInt(2)
    DISKFULL = ShortInt(3)
    ILLEGALOPERATION = ShortInt(4)
    UNKNOWNID = ShortInt(5)
    FILEEXISTS = ShortInt(6)
    NOSUCHUSER = ShortInt(7)

    @classmethod
    def from_bytes(cls, buf):
        return cls(ShortInt.from_bytes(buf))

    def to_bytes(self):
        return self.value.to_bytes()
