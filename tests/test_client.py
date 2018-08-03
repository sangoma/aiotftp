import aiotftp
import pytest


@pytest.mark.asyncio
async def test_read(filename, contents, server, event_loop):
    url = 'tftp://127.0.0.1:1069/{}'.format(filename)

    response = aiotftp.read(url, loop=event_loop)
    async with response:
        assert await response.data() == contents


@pytest.mark.asyncio
async def test_read_notfound(server, event_loop):
    url = 'tftp://127.0.0.1:1069/notfound'

    response = aiotftp.read(url, loop=event_loop)
    with pytest.raises(FileNotFoundError):
        async with response:
            await response.data()


@pytest.mark.asyncio
async def test_write(filename, contents, server, event_loop):
    url = 'tftp://127.0.0.1:1069/{}'.format(filename)

    await aiotftp.write(url, data=contents, loop=event_loop)
    assert await server.wrq_files[filename] == contents


@pytest.mark.asyncio
async def test_write_notfound(server, event_loop):
    url = 'tftp://127.0.0.1:1069/notfound'

    with pytest.raises(RuntimeError):
        await aiotftp.write(url, data=b'hello', loop=event_loop)
