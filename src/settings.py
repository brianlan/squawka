import logging
import datetime
import os


FIXED_HEADERS = {'Host': 'www.squawka.com',
                 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:26.0) Gecko/20100101 Firefox/26.0',
                 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                 'Accept-Encoding': 'deflate',
                 'Connection': 'keep-alive'}

LOG_DIR = 'log'

logger = logging.getLogger('skynet-portal')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(os.path.sep.join([
    LOG_DIR if os.path.isdir(LOG_DIR) and os.access(LOG_DIR, os.W_OK) else '/tmp',
    datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')
]))
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)
