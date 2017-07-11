import pytest
from aiotftp import PacketError
from aiotftp.mode import Mode


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
    with pytest.raises(PacketError):
        Mode.from_string(modestr)


@pytest.mark.parametrize("mode,expected", [
    (Mode.NETASCII, b"netascii"),
    (Mode.OCTET, b"octet"),
])
def test_mode_to_bytes(mode, expected):
    assert mode.to_bytes() == expected
