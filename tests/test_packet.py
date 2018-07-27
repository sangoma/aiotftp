from aiotftp.packet import (AckPacket, DataPacket, ErrorCode, ErrorPacket,
                            RequestPacket, create_packet, parse_packet)
from aiotftp.parser import Mode, Opcode
import pytest


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


@pytest.mark.parametrize("kwargs", [{
    "opcode": Opcode.ACK,
}, {
    "opcode": Opcode.WRQ,
    "error_code": ErrorCode.NOTDEFINED,
    "error_msg": "whatever",
}, {
    "opcode": Opcode.DATA,
    "block_no": 10,
}])
def test_invalid_create_packet(kwargs):
    with pytest.raises(ValueError):
        create_packet(**kwargs)


@pytest.mark.parametrize("buf", [
    b"\x00\x01filename.txt\x00NETASCII\x00",
    b"\x00\x02file\x00OcTet\x00",
    b"\x00\x03\x00\x02some data\x99",
    b"\x00\x04\x01\x04",
    b"\x00\x05\x00\x07no such user\x00",
])
def test_valid_parse_packet(buf):
    assert parse_packet(buf)


@pytest.mark.parametrize("buf", [
    b"\x04\x08filename.txt\x00NETASCII\x00",
    b"\x00\x02file\x00Ocet\x00",
    b"\x00\x04\x01",
    b"",
])
def test_invalid_parse_packet(buf):
    with pytest.raises(ValueError):
        parse_packet(buf)
