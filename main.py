import asyncio

from src.crawl import process_entry_page, process_match
from src.settings import RESULT_URL_BASE, DEFAULT_LEAGUE, DEFAULT_SEASON


if __name__ == '__main__':
    # TODO: add row_cre_ts for each table
    # TODO: write scheduler myself
    # TODO: make the absolute interval random to prevent regular accessing pattern been discovered by squawka
    # TODO: use argparse to specify detailed behavior of this crawler
    result_entry_url = f'{RESULT_URL_BASE}?ctl={DEFAULT_LEAGUE}_s{DEFAULT_SEASON}'

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([process_entry_page(result_entry_url, loop, 2), process_match(loop)]))
    loop.close()
