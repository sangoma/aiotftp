from .packet import create_packet, parse_packet  # noqa
from .protocol import RequestHandler
from .transfers import FileResponse, Response  # noqa


class Server:
    def __init__(self, rrq, wrq, *, timeout=None, loop=None):
        self._loop = None
        self.rrq = rrq
        self.wrq = wrq
        self.timeout = timeout

    def __call__(self):
        return RequestHandler(
            self.rrq, self.wrq, timeout=self.timeout, loop=self._loop)
