import enum
from aiotftp.exceptions import PacketError


class Mode(enum.Enum):
    NETASCII = "netascii"
    OCTET = "octet"
    MAIL = "mail"

    @classmethod
    def from_string(cls, s):
        s = s.lower()
        if s == Mode.NETASCII.value:
            return Mode.NETASCII
        if s == Mode.OCTET.value:
            return Mode.OCTET
        if s == Mode.MAIL.value:
            raise PacketError(f"MAIL mode is intentionally not implemented")

        raise PacketError(f"invalid mode '{s}'")

    def to_bytes(self):
        return bytes(self.value, encoding="ascii")
