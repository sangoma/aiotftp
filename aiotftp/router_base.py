from typing import Union
from typing.io import IO
from aiotftp.packet import RequestPacket
from aiotftp.packet import ErrorPacket


class TftpRouter:
    def rrq_recieved(self,
                     packet: RequestPacket,
                     remote_addr
                     ) -> Union[IO[bytes], ErrorPacket]:
        """Return either an IO object to read from, or an ErrorPacket."""
        raise NotImplementedError

    def wrq_recieved(self,
                     packet: RequestPacket,
                     remote_addr
                     ) -> Union[IO[bytes], ErrorPacket]:
        """Return either the IO object to write to, or an ErrorPacket."""
        raise NotImplementedError

    def wrq_complete(self, buffer: IO[bytes], remote_addr):
        """Recieve previously supplied IO object after the WRQ completes."""
        raise NotImplementedError
