import asyncio
from aiotftp.packet import create_packet
from aiotftp.packet import parse_packet
from aiotftp.opcode import Opcode


class TftpReadProtocol(asyncio.DatagramProtocol):
    """A RRQ protocol to serve bytes from a file-like object."""
    def __init__(self, remote, buffer, callback=None, timeout=2.0):
        self.buffer = buffer
        self.remote = remote
        self.callback = callback
        self.timeout = timeout
        self.loop = asyncio.get_event_loop()

        self.block_no = 0
        self.cur_buffer = None
        self.at_end_of_file = False
        self.transmit_loop_handle = None

    def connection_made(self, transport):
        self.transport = transport
        self.load_next_packet()
        self.transmit_loop()

    def connection_lost(self, exc):
        if self.callback:
            self.callback()

    def datagram_received(self, buffer, remote):
        """Handle the ACKs for DATA packets sent."""
        if remote[1] != self.remote[1]:
            return

        packet = parse_packet(buffer)
        if packet.opcode == Opcode.ACK:
            if packet.block_no == self.block_no:
                if self.at_end_of_file:
                    if self.transmit_loop_handle:
                        self.transmit_loop_handle.cancel()
                    self.transport.close()
                else:
                    self.load_next_packet()
                    self.reset_transmit_loop()

    def transmit_loop(self):
        """Transmit the current buffer and schedule another transmission.

        This will transmit when first called and ever `timeout` seconds
        thereafter, unless `reset_transmit_loop()` is called
        """
        self.transport.sendto(self.cur_buffer, self.remote)
        self.transmit_loop_handle = self.loop.call_later(self.timeout,
                                                         self.transmit_loop)

    def reset_transmit_loop(self):
        self.transmit_loop_handle.cancel()
        self.transmit_loop()

    def load_next_packet(self):
        self.block_no += 1
        buffer = self.buffer.read(512)
        if len(buffer) < 512:
            self.at_end_of_file = True
        self.cur_buffer = create_packet(Opcode.DATA,
                                        block_no=self.block_no,
                                        data=buffer).to_bytes()
