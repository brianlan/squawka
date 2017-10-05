import logging
import datetime
import os
import yaml


#####################
#  Load Auth file   #
#####################
with open('auth.yml', 'r') as f:
    AUTH = yaml.load(f)

#####################################
#   Settings for different Stages   #
#####################################
TEST_CONFIG = {
    'data_db': {
        'mysql': {
            'host': 'mysql',
            'port': 3306,
        }
    }
}

DOCKER_COMPOSE_DEPLOY_CONFIG = {
    'data_db': {
        'mysql': {
            'host': 'mysql',
            'port': 3306,
        }
    }
}

FULL_CONFIG = {
    'prod': {
        'deploy': DOCKER_COMPOSE_DEPLOY_CONFIG,
        'test': TEST_CONFIG
    },

    'rc': {
        'deploy': DOCKER_COMPOSE_DEPLOY_CONFIG,
        'test': TEST_CONFIG
    },

    'dev': {
        'deploy': DOCKER_COMPOSE_DEPLOY_CONFIG,
        'test': TEST_CONFIG
    },

    'local': {
        'deploy': {
            'data_db': {
                'mysql': {
                    'host': 'localhost',
                    'port': 33306,
                    'username': AUTH['localhost_infra_mysql']['username'],
                    'password': AUTH['localhost_infra_mysql']['password']
                }
            }
        },
        'test': TEST_CONFIG
    }
}

CONFIG = FULL_CONFIG[os.environ['SQUAWKA_RUNTIME_STAGE']][os.environ['SQUAWKA_RUNTIME_MODE']]


def get_config(stage, mode):
    return FULL_CONFIG[stage][mode]


#####################
#   Create logger   #
#####################
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
