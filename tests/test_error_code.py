import pytest
from aiotftp import PacketError
from aiotftp.error_code import ErrorCode


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
    with pytest.raises(PacketError):
        ErrorCode.from_bytes(buf)


@pytest.mark.parametrize("code,expected", [
    (ErrorCode.NOSUCHUSER, b"\x00\x07"),
    (ErrorCode.NOTDEFINED, b"\x00\x00"),
])
def test_error_code(code, expected):
    assert code.to_bytes() == expected
