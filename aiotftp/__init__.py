import asyncio

from .exceptions import AioTftpError, PacketError  # noqa
from .packet import create_packet, parse_packet  # noqa
from .router_base import TftpRouter  # noqa
from .server_protocol import TftpProtocol


def create_tftp_server(tftp_factory, *, loop=None, local_addr=None, **kwargs):
    if not loop:
        loop = asyncio.get_event_loop()

    return loop.create_datagram_endpoint(
        lambda: TftpProtocol(tftp_factory(), **kwargs),
        local_addr=local_addr or ('0.0.0.0', 69))
