import enum
from aiotftp import PacketError
from aiotftp.short_int import ShortInt


class Opcode(enum.Enum):
    RRQ = ShortInt(1)
    WRQ = ShortInt(2)
    DATA = ShortInt(3)
    ACK = ShortInt(4)
    ERROR = ShortInt(5)

    @classmethod
    def from_bytes(cls, buf):
        i = ShortInt.from_bytes(buf)
        for opcd in cls:
            if i == opcd.value:
                return opcd
        raise PacketError("invalid opcode '{}'".format(i))

    def is_request(self):
        return self in [Opcode.RRQ, Opcode.WRQ]

    def to_bytes(self):
        return self.value.to_bytes()
