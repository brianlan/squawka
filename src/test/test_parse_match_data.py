import sys
import xml.etree.ElementTree as ET
sys.path.append('..')

from ..processor import Match


def test_parse_message():
    tree = ET.parse('squawka.xml')
    root = tree.getroot()

    match = Match(root)
    assert len(match.event_groups) == 20
    tavares_gomes_9280_passes = [e for e in match.event_groups['all_passes'] if e.player.id == 9280]
    tavares_gomes_9280_crosses = [e for e in match.event_groups['crosses'] if e.player.id == 9280]
    assert len(tavares_gomes_9280_passes) == 3
    assert len(tavares_gomes_9280_crosses) == 1
    [print(p) for p in tavares_gomes_9280_passes]
    [print(p) for p in tavares_gomes_9280_crosses]
    pass