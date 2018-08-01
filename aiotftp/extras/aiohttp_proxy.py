import aiohttp
import aiotftp


async def proxy_from_url(request, url):
    transfer = aiotftp.StreamResponse()

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise FileNotFoundError()

            await transfer.prepare(request)
            while True:
                chunk = await resp.content.read(8192)
                if not chunk:
                    break
                await transfer.write(chunk)

    return transfer
