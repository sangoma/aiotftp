from typing import Union
from typing.io import IO

from aiotftp.packet import ErrorPacket, RequestPacket


class TftpRouter:
    def rrq_recieved(self, packet: RequestPacket,
                     remote_addr) -> Union[IO[bytes], ErrorPacket]:
        """Return either an IO object to read from, or an ErrorPacket."""

    def rrq_complete(self, filename, remote_addr):
        """Called when previously recieved rrq is completed."""

    def wrq_recieved(self, packet: RequestPacket,
                     remote_addr) -> Union[IO[bytes], ErrorPacket]:
        """Return either the IO object to write to, or an ErrorPacket."""

    def wrq_complete(self, buffer: IO[bytes], filename, remote_addr):
        """Recieve previously supplied IO object after the WRQ completes."""
