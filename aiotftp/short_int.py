from aiotftp import AioTftpError


class ShortInt(int):
    """Convenience class for the often-used short int."""

    @classmethod
    def from_bytes(self, buf):
        if len(buf) != 2:
            raise AioTftpError("ShortInt requires exactly 2"
                               " bytes, {} recieved".format(len(buf)))
        return int.from_bytes(buf, byteorder="big")

    def to_bytes(self):
        return int.to_bytes(self, length=2, byteorder="big")
