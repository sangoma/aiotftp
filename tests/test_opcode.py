import pytest
from aiotftp import PacketError
from aiotftp.short_int import ShortInt
from aiotftp.opcode import Opcode


def opcode_bytes(i):
    return ShortInt(i).to_bytes()


@pytest.mark.parametrize("op", [x for x in range(1, 6)])
def test_valid_opcode_from_bytes(op):
    assert Opcode.from_bytes(opcode_bytes(op)).value == op


@pytest.mark.parametrize("op", [0, 6])
def test_invalid_opcode_from_bytes(op):
    with pytest.raises(PacketError):
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
