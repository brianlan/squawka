import re
import asyncio

from aiohttp import ClientSession
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

from .error import UnrecognizedURLFormat, PageNumNotPresentInURL
from .models import Match
from .utils import jitter, get_league_name, retry
from .settings import RESULT_URL_BASE, MATCH_CONSUME_INTERVAL, MAX_NUM_RETRY, RETRY_INTERVAL, logger


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
            raise UnrecognizedURLFormat(f'Cannot convert {pg_num_str} to int in {url}. err_msg: {e}')

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


@retry(max_retry=MAX_NUM_RETRY, sec_to_sleep=RETRY_INTERVAL, logger=logger)
async def get_result_page_content(sess, url):
    async with sess.get(url) as resp:
        return await resp.text()


async def enqueue_matches(match_urls, loop, one_off=False):
    [await enqueue_if_not_exist(m, loop) for m in match_urls]
    if one_off:
        await queue.put(None)


async def produce_matches(result_page_url, loop, latest=None, one_off=False):
    """produce matches from result page url

    :param result_page_url:
    :param loop:
    :param latest: if None, will process all pages, otherwise will only process latest several days that been given.
    :param one_off: indicates whether the process should go in infinite schedules
    :return:
    """
    async with ClientSession(loop=loop) as sess:
        cur_pg = ResultPage(result_page_url, await get_result_page_content(sess, result_page_url))
        await enqueue_matches(cur_pg.get_match_urls(), loop)

        if one_off:
            await queue.put(None)
        else:
            max_pg_num = cur_pg.get_max_page_num()
            pg_urls = cur_pg.generate_result_urls(max_pg_num) if latest is None else cur_pg.generate_result_urls(latest)
            for pg_url in pg_urls:
                await asyncio.sleep(jitter(15))
                pg = ResultPage(pg_url, await get_result_page_content(sess, pg_url))
                await enqueue_matches(pg.get_match_urls(), loop)


@retry(max_retry=MAX_NUM_RETRY, sec_to_sleep=RETRY_INTERVAL, logger=logger)
async def get_data_xml(match_url, loop):
    async with ClientSession(loop=loop) as sess:
        async with sess.get(match_url) as resp:
            text = await resp.text()

        m = re.search("chatClient\.roomID\s*=\s*parseInt\(\\'(\d+)\\'\)", text)
        match_id = m.group(1)

        # chat_data_url = f'http://s3-irl-laliga.squawka.com/chat/{match_id}'
        ingame_data_url3 = f'http://s3-irl-{get_league_name(match_url)}.squawka.com/dp/ingame/{match_id}'
        # ingame_rdp_data_url2 = f'http://s3-irl-laliga.squawka.com/dp/ingame_rdp/{match_id}'

        async with sess.get(ingame_data_url3) as resp:
            data = await resp.text()

        return int(match_id), ET.fromstring(data)


async def process_match(loop):
    while True:
        logger.info('Waiting for match url in queue...')
        url = await queue.get()

        if url is None:
            logger.info('Stop signal received. End process_match.')
            break

        logger.info('Consume match {} from queue. Start to process.'.format(url))
        match_id, root = await get_data_xml(url, loop)

        if root.tag == 'Error':
            logger.warn('Data of match {} not ready yet. Skip this time.'.format(url))
        else:
            match = Match(url, root, match_id)
            await match.save(loop)
            logger.info('Match {} is done.'.format(url))

        queue.task_done()
        logger.info('Sleep for a while...')
        await asyncio.sleep(jitter(MATCH_CONSUME_INTERVAL))
        logger.info("Wake up from sleep. I'm going to work now.")
