import asyncio
import logging

import aiotftp


async def main(loop):
    async with aiotftp.read('tftp://127.0.0.1/pubkey.txt') as response:
        contents = await response.data()
        print(contents.decode())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main(loop))
    except KeyboardInterrupt:
        pass
    loop.close()
