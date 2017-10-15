import re
import sys
import xml.etree.ElementTree as ET
sys.path.append('..')

from aiohttp import ClientSession
import pytest

from ..models import Match, DBConnection


@pytest.mark.asyncio
async def test_any(event_loop):
    # url = 'http://la-liga.squawka.com/spanish-la-liga/01-10-2017/barcelona-vs-las-palmas/matches'
    url = 'http://la-liga.squawka.com/spanish-la-liga/20-09-2017/r-madrid-vs-betis/matches'
    async with ClientSession(loop=event_loop) as sess:
        async with sess.get(url) as resp:
            text = await resp.text()

        m = re.search("chatClient\.roomID\s*=\s*parseInt\(\\'(\d+)\\'\)", text)
        match_id = m.group(1)

        chat_data_url = f'http://s3-irl-laliga.squawka.com/chat/{match_id}'
        ingame_data_url3 = f'http://s3-irl-laliga.squawka.com/dp/ingame/{match_id}'
        ingame_rdp_data_url2 = f'http://s3-irl-laliga.squawka.com/dp/ingame_rdp/{match_id}'

        async with sess.get(ingame_data_url3) as resp:
            data = await resp.text()

        root = ET.fromstring(data)

    pass

