from functools import partial
import string

from aiotftp import packet
from aiotftp.packet import ushort, parse_ushort
from hypothesis import given
import hypothesis.strategies as st
import pytest

unicode_escape = partial(bytes.decode, encoding='unicode_escape')


@pytest.mark.parametrize("buf", [
    b"\x00\x01filename.txt\x00NETASCII\x00",
    b"\x00\x02file\x00OcTet\x00",
    b"\x00\x03\x00\x02some data\x99",
    b"\x00\x04\x01\x04",
    b"\x00\x05\x00\x07no such user\x00",
], ids=unicode_escape)
def test_parse_valid_packet(buf):
    assert packet.parse(buf)


@pytest.mark.parametrize("buf", [
    b"\x04\x08filename.txt\x00NETASCII\x00",
    b"\x00\x02file\x00Ocet\x00",
    b"\x00\x04\x01",
    b"",
    b"\x00\x05\x00\x0Fno such user\x00",
], ids=unicode_escape)
def test_parse_invalid_packet(buf):
    with pytest.raises(ValueError):
        packet.parse(buf)


ushorts = st.integers(min_value=0, max_value=65535)
ascii_text = st.text(alphabet=string.ascii_letters)


@given(st.binary(min_size=2, max_size=2))
def test_parsing_ushort(buf):
    assert ushort(parse_ushort(buf)) == buf


opcodes = st.sampled_from([packet.Opcode.RRQ, packet.Opcode.WRQ])
modes = st.sampled_from(packet.Mode)
request_packets = st.builds(
    packet.Request, opcode=opcodes, filename=ascii_text, mode=modes)


@given(request_packets)
def test_request_packets(pkt):
    data = bytes(pkt)
    assert packet.parse(data) == pkt


data_packets = st.builds(
    packet.Data, block_no=ushorts, data=st.binary(max_size=512))


@given(data_packets)
def test_data_packets(pkt):
    data = bytes(pkt)
    assert packet.parse(data) == pkt


ack_packets = st.builds(packet.Ack, block_no=ushorts)


@given(ack_packets)
def test_ack_packets(pkt):
    ack = bytes(pkt)
    assert packet.parse(ack) == pkt


error_codes = st.sampled_from(packet.ErrorCode)
error_packets = st.builds(packet.Error, code=error_codes, message=ascii_text)


@given(error_packets)
def test_error_packets(pkt):
    data = bytes(pkt)
    assert packet.parse(data) == pkt
