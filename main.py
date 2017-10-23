import asyncio
import argparse

from src.crawl import produce_matches, process_match, enqueue_matches
from src.settings import CHECK_LATEST_RESULT_PAGE


parser = argparse.ArgumentParser(description='Crawl data from website.')
parser.add_argument('--mode', required=True, choices=['daemon', 'result', 'match'], help='mode of the program')
parser.add_argument('--related-url', required=True, type=str, help='related url could be used in all modes')
parser.add_argument('--num-latest-pages', type=int, default=CHECK_LATEST_RESULT_PAGE,
                    help='number of result pages to check in daemon mode.')


if __name__ == '__main__':
    # TODO: write scheduler myself
    # result_entry_url = f'{RESULT_URL_BASE}?ctl={DEFAULT_LEAGUE}_s{DEFAULT_SEASON}'
    args = parser.parse_args()
    loop = asyncio.get_event_loop()
    tasks = [process_match(loop)]
    if args.mode == 'match':
        tasks.append(enqueue_matches([args.related_url], loop, one_off=True))
    elif args.mode == 'result':
        tasks.append(produce_matches(args.related_url, loop, latest=1, one_off=True))
    elif args.mode == 'daemon':
        tasks.append(produce_matches(args.related_url, loop, latest=args.num_latest_pages))

    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
