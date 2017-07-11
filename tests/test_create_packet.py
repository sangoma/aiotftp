import pytest
from aiotftp import AioTftpError
from aiotftp.mode import Mode
from aiotftp.opcode import Opcode
from aiotftp.packet import AckPacket
from aiotftp.packet import DataPacket
from aiotftp.packet import ErrorCode
from aiotftp.packet import ErrorPacket
from aiotftp.packet import RequestPacket
from aiotftp.packet import create_packet


@pytest.mark.parametrize("kwargs,expected_class", [
    ({
        "opcode": Opcode.RRQ,
        "filename": "file.txt",
        "mode": Mode.OCTET,
    }, RequestPacket),
    ({
        "opcode": Opcode.WRQ,
        "filename": "file.txt",
        "mode": Mode.NETASCII,
    }, RequestPacket),
    ({
        "opcode": Opcode.DATA,
        "block_no": 10,
        "data": b"\x01\x02",
    }, DataPacket),
    ({
        "opcode": Opcode.ACK,
        "block_no": 10,
    }, AckPacket),
    ({
        "opcode": Opcode.ERROR,
        "error_code": ErrorCode.DISKFULL,
        "error_msg": "disk full",
    }, ErrorPacket),
])
def test_valid_create_packet(kwargs, expected_class):
    pkt = create_packet(**kwargs)
    assert isinstance(pkt, expected_class)
    for key, val in kwargs.items():
        assert getattr(pkt, key) == val


@pytest.mark.parametrize("kwargs", [
    {
        "opcode": Opcode.ACK,
    },
    {
        "opcode": Opcode.WRQ,
        "error_code": ErrorCode.NOTDEFINED,
        "error_msg": "whatever",
    },
    {
        "opcode": Opcode.DATA,
        "block_no": 10,
    }
])
def test_invalid_create_packet(kwargs):
    with pytest.raises(AioTftpError):
        create_packet(**kwargs)

