import sys
import datetime
from pytz import timezone as tz
import xml.etree.ElementTree as ET
sys.path.append('..')

from ..models import Match


# Barcelona 3 - 0 Las Palmas on 2017-10-01
def test_parse_match():
    tree = ET.parse('squawka.xml')
    root = tree.getroot()
    match = Match(root, 1, 2)

    assert match.summary == 'Barcelona 3 - 0 Las Palmas'
    assert f'{match.date.year}-{match.date.month}-{match.date.day}' == '2017-10-1'
    assert f'{match.date.hour}:{match.date.minute}' == '15:15'
    assert match.stadium == 'Camp Nou'
    assert match.home_team.id == 73
    assert match.away_team.id == 525
    assert match.home_team.name == 'Barcelona'
    assert match.away_team.name == 'Las Palmas'
    assert match.home_score == 3
    assert match.away_score == 0

    assert len(match.event_groups) == 20

    tavares_gomes_9280_passes = [e for e in match.event_groups['all_passes'] if e.player_id == 9280]
    tavares_gomes_9280_crosses = [e for e in match.event_groups['crosses'] if e.player_id == 9280]
    tavares_gomes_9280_tackles = [e for e in match.event_groups['tackles'] if e.player_id == 9280]
    assert len(tavares_gomes_9280_passes) == 3
    assert len(tavares_gomes_9280_crosses) == 1
    assert len(tavares_gomes_9280_tackles) == 1
    [print(p) for p in tavares_gomes_9280_passes]
    [print(p) for p in tavares_gomes_9280_crosses]
    [print(p) for p in tavares_gomes_9280_tackles]

    ivan_rakitic_12_shots = [e for e in match.event_groups['goals_attempts'] if e.player_id == 12]
    assert len(ivan_rakitic_12_shots) == 3
    [print(p) for p in ivan_rakitic_12_shots]

    oussama_tannane_7867_shot = [e for e in match.event_groups['goals_attempts'] if e.player_id == 7867]
    assert len(oussama_tannane_7867_shot) == 3
    [print(p) for p in oussama_tannane_7867_shot]

    messi_1569_corner = [e for e in match.event_groups['corners'] if e.player_id == 1569]
    assert len(messi_1569_corner) == 3
    [print(p) for p in messi_1569_corner]


# R Madrid 0 - 1 Betis on 2017-09-20
def test_parse_match2():
    tree = ET.parse('squawka2.xml')
    root = tree.getroot()
    match = Match(root, 1, 2)
    assert len(match.event_groups) == 20

    assert match.summary == 'R Madrid 0 - 1 Betis'
    assert f'{match.date.year}-{match.date.month}-{match.date.day}' == '2017-9-20'
    assert f'{match.date.hour}:{match.date.minute}' == '21:0'
    assert match.stadium == 'Santiago Bernabéu'
    assert match.home_team.id == 85
    assert match.away_team.id == 84
    assert match.home_team.name == 'Real Madrid'
    assert match.away_team.name == 'Real Betis'
    assert match.home_score == 0
    assert match.away_score == 1

    # Gareth Bale (ID: 843)
    assert len([e for e in match.event_groups['goals_attempts'] if e.player_id == 843]) == 2
    assert len([e for e in match.event_groups['all_passes'] if e.player_id == 843]) == 38
    assert len([e for e in match.event_groups['crosses'] if e.player_id == 843]) == 7
    assert len([e for e in match.event_groups['tackles'] if e.player_id == 843]) == 2
    assert len([e for e in match.event_groups['clearances'] if e.player_id == 843]) == 1
    assert len([e for e in match.event_groups['blocked_events'] if e.player_id == 843]) == 2

    # Cristiano Ronaldo (ID: 232)
    assert len([e for e in match.event_groups['goals_attempts'] if e.player_id == 232]) == 12
    assert len([e for e in match.event_groups['all_passes'] if e.player_id == 232]) == 28
    assert len([e for e in match.event_groups['crosses'] if e.player_id == 232]) == 1
    assert len([e for e in match.event_groups['takeons'] if e.player_id == 232]) == 1
    assert len([e for e in match.event_groups['headed_duals'] if e.player_id == 232]) == 5
    assert len([e for e in match.event_groups['clearances'] if e.player_id == 232]) == 1
    assert len([e for e in match.event_groups['fouls'] if e.player_id == 232]) == 3


def test_parse_player_info():
    tree = ET.parse('squawka.xml')
    root = tree.getroot()
    match = Match(root, 1, 2)
    assert len(match.participants) == 36
    assert match.participants[0].player.name == 'Marc-André ter Stegen'
    assert match.participants[0].player.country == 'Germany'
    assert match.participants[0].player.weight == 85
    assert match.participants[0].player.height == 187
    assert match.participants[0].player.dob == datetime.datetime(1992, 4, 30)
    assert match.participants[0].player.id == 2088
    assert match.participants[0].player.team_id == 73
