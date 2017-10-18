import sys
sys.path.append('..')

from ..crawl import ResultPage


def test_generate_all_urls_from_last_page_url():
    entry_page = ResultPage('http://www.squawka.com/match-results?ctl=-1_s2017', soup='dummy')
    urls = entry_page.generate_result_urls(25)
    assert len(urls) == 25
    for i in range(25):
        assert urls[i] == f'http://www.squawka.com/match-results?ctl=-1_s2017&pg={i+1}'


def test_parse_league_id_from_result_page_url():
    entry_page = ResultPage('http://www.squawka.com/match-results?ctl=-1_s2017', soup='dummy')
    assert entry_page.league_id == '-1'


def test_parse_season_from_result_page_url():
    entry_page = ResultPage('http://www.squawka.com/match-results?ctl=-1_s2017', soup='dummy')
    assert entry_page.season == '2017'
