import asyncio
import argparse
import logging

import aiotftp


async def main(loop):
    parser = argparse.ArgumentParser(description='Fetch files over TFTP')
    parser.add_argument('url', type=str)
    parser.add_argument('file', type=str)

    args = parser.parse_args()
    with open(args.file, 'rb') as fobj:
        await aiotftp.write(args.url, data=fobj)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    loop = asyncio.get_event_loop()

    try:
        loop.run_until_complete(main(loop))
    except KeyboardInterrupt:
        pass
    loop.close()
