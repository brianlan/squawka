import re
import asyncio

from aiohttp import ClientSession
import xml.etree.ElementTree as ET

from src.models import Match


async def get_data_xml(match_url, loop):
    async with ClientSession(loop=loop) as sess:
        async with sess.get(match_url) as resp:
            text = await resp.text()

        m = re.search("chatClient\.roomID\s*=\s*parseInt\(\\'(\d+)\\'\)", text)
        match_id = m.group(1)

        # chat_data_url = f'http://s3-irl-laliga.squawka.com/chat/{match_id}'
        ingame_data_url3 = f'http://s3-irl-laliga.squawka.com/dp/ingame/{match_id}'
        # ingame_rdp_data_url2 = f'http://s3-irl-laliga.squawka.com/dp/ingame_rdp/{match_id}'

        async with sess.get(ingame_data_url3) as resp:
            data = await resp.text()

        return int(match_id), ET.fromstring(data)


async def process_match(url, loop, league_id):
    match_id, root = await get_data_xml(url, loop)
    match = Match(root, league_id, match_id)
    await match.save(loop)


if __name__ == '__main__':
    # TODO: add row_cre_ts for each table
    # TODO: use apscheduler
    # TODO: cron producer job to run every day (5 job for 5 different leagues), insert todo-match in queue
    # TODO: cron consumer job to run every 30 min to process a match in queue
    # TODO: use argparse to specify detailed behavior of this crawler
    result_url = 'http://www.squawka.com/match-results?ctl=23_s2017'
    match_url = 'http://la-liga.squawka.com/spanish-la-liga/01-10-2017/valencia-vs-athletic/matches'

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([process_match(match_url, loop, 23)]))
    loop.close()
