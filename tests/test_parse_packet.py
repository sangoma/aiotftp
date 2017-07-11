import pytest
from aiotftp import AioTftpError
from aiotftp.packet import parse_packet


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
    with pytest.raises(AioTftpError):
        parse_packet(buf)
