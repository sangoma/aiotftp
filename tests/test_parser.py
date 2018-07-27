import pytest
from aiotftp.packet import parse_packet
from aiotftp.parser import ErrorCode, Mode, Opcode, ShortInt


@pytest.mark.parametrize("buf,expected", [
    (b"\x00\x00", 0),
    (b"\x00\x01", 1),
    (b"\x01\x00", 256),
])
def test_short_int_from_bytes(buf, expected):
    assert ShortInt.from_bytes(buf) == expected


@pytest.mark.parametrize("i,expected", [
    (0, b"\x00\x00"),
    (1, b"\x00\x01"),
    (256, b"\x01\x00"),
])
def test_short_int_to_bytes(i, expected):
    assert ShortInt(i).to_bytes() == expected


@pytest.mark.parametrize("buf,expected", [
    (b"\x00\x07", ErrorCode.NOSUCHUSER),
    (b"\x00\x00", ErrorCode.NOTDEFINED),
])
def test_valid_error_code(buf, expected):
    assert ErrorCode.from_bytes(buf) == expected


@pytest.mark.parametrize("buf", [
    b"\x00\x08",
    b"\x01\x00",
])
def test_invalid_error_code(buf):
    with pytest.raises(ValueError):
        ErrorCode.from_bytes(buf)


@pytest.mark.parametrize("code,expected", [
    (ErrorCode.NOSUCHUSER, b"\x00\x07"),
    (ErrorCode.NOTDEFINED, b"\x00\x00"),
])
def test_error_code(code, expected):
    assert code.to_bytes() == expected


@pytest.mark.parametrize("modestr,expected", [
    ("netascii", Mode.NETASCII),
    ("NETASCII", Mode.NETASCII),
    ("OCTet", Mode.OCTET),
    ("Octet", Mode.OCTET),
])
def test_valid_mode_from_string(modestr, expected):
    assert Mode.from_string(modestr) == expected


@pytest.mark.parametrize("modestr", [
    "netasci",
    "ocet",
    "foobar",
])
def test_invalid_mode_from_string(modestr):
    with pytest.raises(ValueError):
        Mode.from_string(modestr)


@pytest.mark.parametrize("mode,expected", [
    (Mode.NETASCII, b"netascii"),
    (Mode.OCTET, b"octet"),
])
def test_mode_to_bytes(mode, expected):
    assert mode.to_bytes() == expected


def opcode_bytes(i):
    return ShortInt(i).to_bytes()


@pytest.mark.parametrize("op", [x for x in range(1, 6)])
def test_valid_opcode_from_bytes(op):
    assert Opcode.from_bytes(opcode_bytes(op)).value == op


@pytest.mark.parametrize("op", [0, 6])
def test_invalid_opcode_from_bytes(op):
    with pytest.raises(ValueError):
        Opcode.from_bytes(opcode_bytes(op))


@pytest.mark.parametrize("opcode,expected", [
    (Opcode.RRQ, b"\x00\x01"),
    (Opcode.WRQ, b"\x00\x02"),
])
def test_opcode_to_bytes(opcode, expected):
    assert opcode.to_bytes() == expected


@pytest.mark.parametrize("opcode,expected", [
    (Opcode.RRQ, True),
    (Opcode.WRQ, True),
    (Opcode.DATA, False),
])
def test_opcode_is_request(opcode, expected):
    assert opcode.is_request() == expected
