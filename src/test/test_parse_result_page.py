import sys
sys.path.append('..')

from ..crawl import ResultPage


def test_generate_all_urls_from_last_page_url():
    urls = ResultPage.generate_result_urls(25)
    assert len(urls) == 25
    for i in range(25):
        assert urls[i] == f'http://www.squawka.com/match-results?ctl=-1_s2017&pg={i+1}'
