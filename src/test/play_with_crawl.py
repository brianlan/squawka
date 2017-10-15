import sys
import pytest
sys.path.append('..')

from crawl import process_entry_page


@pytest.mark.asyncio
async def test_process_entry_page(event_loop):
    # entry_page = 'http://www.squawka.com/match-results?ctl=23_s2017'
    entry_page = 'http://www.squawka.com/match-results?ctl=-1_s2017&pg=25'
    await process_entry_page(entry_page, event_loop)
