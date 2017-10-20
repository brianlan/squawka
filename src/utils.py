import re
import random


def flatten(x):
    """1-order flatten method"""
    return [j for i in x for j in (i if isinstance(i, list) else [i])]


def jitter(mu, sigma=4):
    return int(random.normalvariate(mu, sigma))


def get_league_name(match_url, short=True):
    pat = r'^http.+//(.+).squawka\.com/.*' if short else r'^http.+//.+.squawka\.com/([a-zA-Z_-]+)/'
    m = re.search(pat, match_url)
    try:
        league_name = m.group(1)
    except AttributeError:
        league_name = 'unknown'
    return league_name
