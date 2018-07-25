import enum

from aiotftp import PacketError
from aiotftp.short_int import ShortInt


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
        i = ShortInt.from_bytes(buf)
        for code in cls:
            if i == code.value:
                return code
        raise PacketError("invalid error code")

    def to_bytes(self):
        return self.value.to_bytes()
