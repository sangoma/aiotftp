import asyncio
import argparse
import logging

import aiotftp


async def main(loop):
    parser = argparse.ArgumentParser(description='Fetch files over TFTP')
    parser.add_argument('url', metavar='URL', type=str)

    args = parser.parse_args()
    async with aiotftp.read(args.url) as response:
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
