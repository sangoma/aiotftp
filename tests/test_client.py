import aiotftp
import pytest


@pytest.mark.asyncio
async def test_read(filename, contents, server, event_loop):
    url = 'tftp://127.0.0.1:1069/{}'.format(filename)

    response = aiotftp.read(url, loop=event_loop)
    async with response:
        assert await response.data() == contents
