import sys
import xml.etree.ElementTree as ET
sys.path.append('..')

from ..processor import Match


def test_parse_message():
    tree = ET.parse('squawka.xml')
    root = tree.getroot()

    match = Match(root)
    assert len(match.event_groups) == 20

    pass