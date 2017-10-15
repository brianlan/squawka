import asyncio

from src.crawl import process_match


if __name__ == '__main__':
    # TODO: add row_cre_ts for each table
    # TODO: use apscheduler
    # TODO: cron producer job to run every day (5 job for 5 different leagues), insert todo-match in queue
    # TODO: cron consumer job to run every 30 min to process a match in queue
    # TODO: use argparse to specify detailed behavior of this crawler
    result_url = 'http://www.squawka.com/match-results?ctl=23_s2017'
    match_url = 'http://la-liga.squawka.com/spanish-la-liga/01-10-2017/valencia-vs-athletic/matches'

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([process_match(match_url, loop)]))
    loop.close()
