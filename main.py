import asyncio

from src.crawl import process_entry_page, process_match
from src.settings import CHECK_LATEST_RESULT_PAGE, RESULT_URL_BASE, DEFAULT_LEAGUE, DEFAULT_SEASON


if __name__ == '__main__':
    # TODO: write scheduler myself
    # TODO: use argparse to specify detailed behavior of this crawler
    result_entry_url = f'{RESULT_URL_BASE}?ctl={DEFAULT_LEAGUE}_s{DEFAULT_SEASON}'
    loop = asyncio.get_event_loop()
    producer, consumer = process_entry_page(result_entry_url, loop, CHECK_LATEST_RESULT_PAGE), process_match(loop)
    loop.run_until_complete(asyncio.wait([producer, consumer]))
    loop.close()
