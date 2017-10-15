import asyncio

from aiohttp import ClientSession
from bs4 import BeautifulSoup

from .error import UnrecognizedURLFormat
from .settings import RESULT_URL_BASE, DEFAULT_LEAGUE, DEFAULT_SEASON


queue = asyncio.Queue()


class ResultPage:
    def __init__(self, html: str=None, soup: BeautifulSoup=None):
        if html is None and soup is None:
            raise ValueError('At least one kind of input should be provided, html text or soup object.')
        self.soup = soup or BeautifulSoup(html, 'html.parser')

    def get_max_page_num(self):
        nav_buttons = self.soup.find_all('a', attrs={'class': 'pageing_text_arrow'})
        last_page_url = set([b['href'] for b in nav_buttons if 'last' in b.string.lower()])
        if not last_page_url:
            return 1
        last_page_url = last_page_url[0]
        pg_pos = last_page_url.find('pg=')
        if pg_pos == -1:
            raise UnrecognizedURLFormat(f'Keyword "pg=" not found in {last_page_url}.')
        try:
            pg_num_str = last_page_url[pg_pos+3:]
            return int(pg_num_str)
        except ValueError as e:
            raise UnrecognizedURLFormat(f'Cannot convert {pg_num_str} to int in {last_page_url}. err_msg: {e}')

    @staticmethod
    def generate_result_urls(max_pg_num=None):
        url_base = f'{RESULT_URL_BASE}?ctl={DEFAULT_LEAGUE}_s{DEFAULT_SEASON}'
        return [f'{url_base}&pg={i+1}' for i in range(max_pg_num)]

    def get_match_urls(self):
        return [td.a['href'] for td in self.soup.find_all('td', attrs={'class': 'match-centre'})]


async def enqueue_if_not_exist(match_url):
    # TODO: check if match_url exists in DB
    # TODO: if not exist, push the match_url to queue
    pass


async def process_entry_page(url, loop, latest=None):
    """process_result_page

    :param url:
    :param loop:
    :param latest: if None, will process all pages, otherwise will only process latest several days that been given.
    :return:
    """
    async with ClientSession(loop=loop) as sess:
        async with sess.get(url) as resp:
            cur_pg = ResultPage(await resp.text())

        max_pg_num = cur_pg.get_max_page_num()
        pg_urls = cur_pg.generate_result_urls(max_pg_num) if latest is None else cur_pg.generate_result_urls(latest)
        result_pages = [cur_pg]
        for pg_url in pg_urls:
            async with sess.get(pg_url) as resp:
                result_pages.append(ResultPage(await resp.text()))

        tasks = [enqueue_if_not_exist(m) for p in result_pages for m in p.get_match_urls()]
        asyncio.wait(tasks)
