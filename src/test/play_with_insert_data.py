import sys
from collections import defaultdict
import datetime

sys.path.append('..')

import pytest
from pytz import timezone as tz
import xml.etree.ElementTree as ET

from ..models import Match, DBConnection


# @pytest.mark.asyncio
# async def test_save_team(event_loop):
#     team = Match(ET.parse('squawka.xml').getroot(), 1, 2).home_team
#     await team.save(event_loop)


@pytest.mark.asyncio
async def test_save_match(event_loop):
    match = Match(ET.parse('squawka.xml').getroot(), 23, 34267)
    match2 = Match(ET.parse('squawka2.xml').getroot(), 23, 34253)
    await match.save(event_loop)
    await match2.save(event_loop)
