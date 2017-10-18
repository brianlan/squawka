import re
import asyncio

from aiohttp import ClientSession
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

from .error import UnrecognizedURLFormat, PageNumNotPresentInURL
from .models import Match
from .settings import RESULT_URL_BASE, RESULT_PAGE_VISIT_INTERVAL, MATCH_CONSUME_INTERVAL, logger


queue = asyncio.Queue()


class ResultPage:
    def __init__(self, url, html: str=None, soup: BeautifulSoup=None):
        self._url = url
        if html is None and soup is None:
            raise ValueError('At least one kind of input should be provided, html text or soup object.')
        self.soup = soup or BeautifulSoup(html, 'html.parser')

    def __repr__(self):
        return self.url

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return self.url == other.url

    @staticmethod
    def _get_page_num_from_url(url):
        pg_pos = url.find('pg=')
        if pg_pos == -1:
            raise PageNumNotPresentInURL(f'Keyword "pg=" not found in {url}.')
        try:
            pg_num_str = url[pg_pos+3:]
            return int(pg_num_str)
        except ValueError as e:
            raise UnrecognizedURLFormat(f'Cannot convert {pg_num_str} to int in {last_page_url}. err_msg: {e}')

    @property
    def url(self):
        try:
            self._get_page_num_from_url(self._url)
            return self._url
        except PageNumNotPresentInURL as e:
            return self._url + '&pg=1'

    def get_max_page_num(self):
        nav_buttons = self.soup.find_all('a', attrs={'class': 'pageing_text_arrow'})
        last_page_url = list(set([b['href'] for b in nav_buttons if 'last' in b.string.lower()]))
        if not last_page_url:
            return 1
        return self._get_page_num_from_url(last_page_url[0])

    @property
    def league_id(self):
        m = re.search(RESULT_URL_BASE + r'\?ctl=([1-9a-zA-Z-]+).*', self.url)
        try:
            league_name = m.group(1)
        except AttributeError as e:
            logger.warn(f'Cannot extract league id out of url: {self.url}. err_msg: {e}')
            league_name = 'unknown'
        return league_name

    @property
    def season(self):
        m = re.search(RESULT_URL_BASE + r'\?ctl=(?:[1-9a-zA-Z-]+)_s(\d+).*', self.url)
        try:
            season = m.group(1)
        except AttributeError as e:
            logger.warn(f'Cannot extract season out of url: {self.url}. err_msg: {e}')
            season = 'unknown'
        return season

    def generate_result_urls(self, max_pg_num=None, exclude_self=True):
        url_base = f'{RESULT_URL_BASE}?ctl={self.league_id}_s{self.season}'
        generated_urls = {f'{url_base}&pg={i+1}' for i in range(max_pg_num)}
        return list(generated_urls - {self.url}) if exclude_self else list(generated_urls)

    def get_match_urls(self):
        return [td.a['href'] for td in self.soup.find_all('td', attrs={'class': 'match-centre'})]


async def enqueue_if_not_exist(match_url, loop):
    if not await Match.exists_in_db(loop, {'url': match_url}):
        await queue.put(match_url)
        logger.info('Put match {} into the queue.'.format(match_url))


async def process_entry_page(url, loop, latest=None):
    """process_result_page

    :param url:
    :param loop:
    :param latest: if None, will process all pages, otherwise will only process latest several days that been given.
    :return:
    """
    async with ClientSession(loop=loop) as sess:
        async with sess.get(url) as resp:
            cur_pg = ResultPage(url, await resp.text())

        max_pg_num = cur_pg.get_max_page_num()
        pg_urls = cur_pg.generate_result_urls(max_pg_num) if latest is None else cur_pg.generate_result_urls(latest)
        result_pages = [cur_pg]
        for pg_url in pg_urls:
            async with sess.get(pg_url) as resp:
                result_pages.append(ResultPage(pg_url, await resp.text()))
                await asyncio.sleep(RESULT_PAGE_VISIT_INTERVAL)

        [await enqueue_if_not_exist(m, loop) for p in result_pages for m in p.get_match_urls()]


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


async def process_match(loop):
    while True:
        logger.info('Waiting for match url in queue...')
        url = await queue.get()
        logger.info('Consume match {} from queue. Start to process.'.format(url))
        match_id, root = await get_data_xml(url, loop)
        match = Match(url, root, match_id)
        await match.save(loop)
        logger.info('Match {} is done.'.format(url))
        queue.task_done()
        logger.info('Sleep for a while...')
        await asyncio.sleep(MATCH_CONSUME_INTERVAL)
        logger.info("Wake up from sleep. I'm going to work now.")
