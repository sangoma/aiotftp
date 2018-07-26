import asyncio
import io

from aiotftp import TftpProtocol, TftpRouter, create_packet
from aiotftp.error_code import ErrorCode
from aiotftp.opcode import Opcode


class Router(TftpRouter):
    def rrq_recieved(self, packet, remote):
        try:
            return open(packet.filename, 'rb')
        except OSError:
            return create_packet(
                Opcode.ERROR,
                error_code=ErrorCode.FILENOTFOUND,
                error_msg="not found")

    def rrq_complete(self, filename, remote):
        print(f"File retreived: {filename}")

    def wrq_recieved(self, packet, remote):
        return io.BytesIO()

    def wrq_complete(self, buffer, filename, remote):
        buffer.seek(0)
        with open(filename, 'wb') as fp:
            fp.write(buffer.read())
        print(f"File uploaded: {filename}")


router = Router()
loop = asyncio.get_event_loop()
listen = loop.create_datagram_endpoint(
    lambda: TftpProtocol(router), ("127.0.0.1", 69))
transport, protocol = loop.run_until_complete(listen)

try:
    loop.run_forever()
finally:
    transport.close()
    loop.close()
