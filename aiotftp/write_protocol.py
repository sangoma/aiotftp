import asyncio
from aiotftp.opcode import Opcode
from aiotftp.packet import create_packet
from aiotftp.packet import parse_packet


class TftpWriteProtocol(asyncio.DatagramProtocol):
    """A WRQ protocol to serve bytes from a file-like object."""
    def __init__(self, remote, buffer, callback):
        self.buffer = buffer
        self.remote = remote
        self.block_no = 1
        self.callback = callback

        self.loop = asyncio.get_event_loop()
        self.transmit_loop_handle = None

    def connection_made(self, transport):
        self.transport = transport
        self.cur_buffer = self.ack_for(block_no=0)
        self.transmit_loop()

    def connection_lost(self, exc):
        self.callback(self.buffer)

    def datagram_received(self, buffer, remote):
        if remote[1] != self.remote[1]:
            return

        packet = parse_packet(buffer)
        if packet.opcode == Opcode.DATA and packet.block_no == self.block_no:
            self.buffer.write(packet.data)

            self.cur_buffer = self.ack_for(self.block_no)
            if len(packet.data) == 512:
                self.reset_transmit_loop()
                self.block_no += 1
            else:
                self.transport.sendto(self.cur_buffer, self.remote)
                if self.transmit_loop_handle:
                    self.transmit_loop_handle.cancel()
                self.transport.close()

    def transmit_loop(self):
        """Transmit the current buffer and schedule another transmission.

        This will transmit when first called and ever `timeout` seconds
        thereafter, unless `reset_transmit_loop()` is called
        """
        self.transport.sendto(self.cur_buffer, self.remote)
        self.transmit_loop_handle = self.loop.call_later(2, self.transmit_loop)

    def reset_transmit_loop(self):
        self.transmit_loop_handle.cancel()
        self.transmit_loop()

    def ack_for(self, block_no):
        packet = create_packet(Opcode.ACK,
                               block_no=block_no)
        return packet.to_bytes()

