import asyncio

from .exceptions import AioTftpError
from .exceptions import PacketError
from .packet import create_packet
from .packet import parse_packet
from .router_base import TftpRouter
from .server_protocol import TftpProtocol


def create_tftp_server(tftp_factory, *, loop=None, local_addr=None):
    if not loop:
        loop = asyncio.get_event_loop()

    return loop.create_datagram_endpoint(
        lambda: TftpProtocol(tftp_factory()),
        local_addr=local_addr or ('0.0.0.0', 69)
    )
