import asyncio
import pytest
from aiotftp import TftpRouter
from aiotftp import TftpProtocol
from aiotftp.error_code import ErrorCode
from aiotftp.mode import Mode
from aiotftp.opcode import Opcode
from aiotftp.packet import create_packet
from aiotftp.packet import parse_packet


@pytest.fixture(scope='session')
def loop():
    return asyncio.get_event_loop()


class ErrorRouter(TftpRouter):
    def rrq_recieved(self, packet, remote):
        return create_packet(Opcode.ERROR,
                             error_code=ErrorCode.FILENOTFOUND,
                             error_msg="not found")

    def wrq_recieved(self, packet, remote):
        return create_packet(Opcode.ERROR,
                             error_code=ErrorCode.FILEEXISTS,
                             error_msg="file exists")


class ErrorClient(asyncio.DatagramProtocol):
    def __init__(self, request, future):
        self.request = request
        self.future = future

    @classmethod
    def with_future(cls, request):
        future = asyncio.Future()
        return cls(request, future), future

    def connection_made(self, transport):
        self.transport = transport
        transport.sendto(self.request.to_bytes(), ("127.0.0.1", 1069))

    def datagram_received(self, data, addr):
        self.transport.close()
        self.future.set_result(parse_packet(data))


@pytest.mark.parametrize("pkt_kwargs,expected_err", [
    ({
        "opcode": Opcode.RRQ,
        "filename": "test",
        "mode": Mode.OCTET,
    }, ErrorCode.FILENOTFOUND),
    ({
        "opcode": Opcode.WRQ,
        "filename": "test",
        "mode": Mode.OCTET,
    }, ErrorCode.FILEEXISTS),
])
def test_error_routing(pkt_kwargs, expected_err, loop):
    listen = loop.create_datagram_endpoint(
        lambda: TftpProtocol(ErrorRouter()),
        local_addr=("127.0.0.1", 1069))
    loop.run_until_complete(listen)

    request = create_packet(**pkt_kwargs)
    client, client_future = ErrorClient.with_future(request)
    connect = loop.create_datagram_endpoint(
        lambda: client,
        remote_addr=("127.0.0.1", 1069))
    loop.run_until_complete(connect)

    loop.run_until_complete(client_future)
    assert client_future.result().error_code == expected_err
