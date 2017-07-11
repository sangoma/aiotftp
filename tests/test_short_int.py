import pytest
from aiotftp.short_int import ShortInt


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
