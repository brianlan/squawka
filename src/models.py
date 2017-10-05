import re
import datetime

from .settings import logger


class Player:
    def __init__(self, root):
        self.id = int(root.attrib.get('id'))
        self.team_id = int(root.attrib.get('team_id'))
        self.name = root.find('name').text.strip()
        self.dob = datetime.datetime.strptime(root.find('dob').text, '%d/%m/%Y')  # date of birth
        self.weight = float(root.find('weight').text) if root.find('weight').text != 'Unknown' else None
        self.height = float(root.find('height').text) if root.find('height').text != 'Unknown' else None
        self.country = root.find('country').text.strip()

    def __repr__(self):
        return f'Player-{self.id}'


class Participant:
    """It's different from Player. It stores player info related only to this match, while PlayerPool is static."""
    def __init__(self, root, match_id):
        self.match_id = match_id
        self.init_loc_x = float(root.find('x_loc').text)
        self.init_loc_y = float(root.find('y_loc').text)
        self.position = root.find('position').text
        self.player = Player(root)
        # self.player = PlayerPool.get(root.attrib.get('id'))

    async def _save_players(self):
        # TODO:
        pass

    async def _save_paticipation(self):
        # TODO:
        pass

    async def save(self):
        self._save_players()
        self._save_paticipation()


# class PlayerPool:
#     pool = {}
#
#     def __init__(self):
#         pass
#
#     def __len__(self):
#         return len(self.pool)
#
#     @classmethod
#     def update(cls, root):
#         [cls.push(p) for p in root]
#
#     @classmethod
#     def get(cls, player_id):
#         return cls.pool.get(str(player_id))
#
#     @classmethod
#     def push(cls, root):
#         player = Player(root)
#         cls.pool.update({str(player.id): player})
#
#     @classmethod
#     def clear(cls):
#         cls.pool = {}


class Team:
    def __init__(self, root):
        self.id = int(root.attrib.get('id'))
        self.name = root.find('long_name').text.strip()
        self.short_name = root.find('short_name').text.strip()

    def __repr__(self):
        return self.name

    async def save(self):
        # TODO:
        pass


class Match:
    def __init__(self, root, league_id, match_id):
        game = root.find('data_panel').find('game')
        teams = list(game.findall('team'))
        self.id = match_id
        self.league_id = league_id
        self.summary = root.find('data_panel').find('system').find('headline').text.strip()
        self.date = datetime.datetime.strptime(game.find('kickoff').text, '%a, %d %b %Y %H:%M:%S %z')
        self.stadium = game.find('venue').text.strip()
        self.home_team = Team(teams[0])
        self.away_team = Team(teams[1])

        m = re.search(r'(\d+) - (\d+)', self.summary)
        self.home_score, self.away_score = int(m.group(1)), int(m.group(2))

        # PlayerPool.update(root.find('data_panel').find('players'))
        self.participants = [Participant(p, self.id) for p in root.find('data_panel').find('players')]
        self.event_groups = {f.tag: EventGroup(f, self.id) for f in root.find('data_panel').find('filters')}

    def __repr__(self):
        return f'{self.summary}'

    async def save(self):
        self.home_team.save()
        self.away_team.save()
        [p.save() for p in self.participants]
        all_events = [e for eg in self.event_groups for e in eg]
        # TODO: insert all_events using insertmany


class EventGroup:
    def __init__(self, root, match_id):
        self.match_id = match_id
        self.events = [Event.from_element_root(e, root.tag, match_id) for tc in root.findall('time_slice')
                       for e in tc.findall('event')]

    def __iter__(self):
        return (e for e in self.events)

    def __repr__(self):
        return f'{self.__class__.__name__} ({len(self.events)})'


class Event:
    attr_key_type = {
        'action_type': str,
        'headed': bool,
        'mins': int,
        'minsec': int,
        'player_id': int,
        'secs': int,
        'team_id': int,
        'type': str,
        'injurytime_play': bool,
        'uid': str,
        'throw_ins': bool,
        'team': int,
        'other_player': int,
        'other_team': int,
        'shot_player': int,
        'shot_team': int,
        'ot_id': int,
        'ot_outcome': bool,
        'gz': float,
        'gy': float,
        'k': bool,
        'a': bool
    }

    def __init__(self, root, match_id):
        self.match_id = match_id
        self.event_type = self.__class__.__name__
        self.counterparty_id = None
        for k, v in root.items():
            if k == 'player_id':
                self.player_id = int(v)
                # self.player = PlayerPool.get(v)
            elif k == 'other_player':
                self.counterparty_id = int(v)
                # self.counterparty = PlayerPool.get(v)
            else:
                try:
                    super().__setattr__(k, self.attr_key_type[k](v))
                except KeyError as e:
                    logger.warn('Type of attr-key {} not been set yet, use str instead. err_msg: {}'.format(k, e))
                    super().__setattr__(k, v)

        self.minsec = self.__dict__.get('minsec') or self.mins * 60 + self.secs

    def __repr__(self):
        base = f'[{self.mins:2}:{self.secs:2}] Player-{self.player_id} {self.__class__.__name__.lower()}'
        final = base + (f' at {self.start}' if self.start == self.end else f' from {self.start} to {self.end}')
        return final

    @classmethod
    def from_element_root(cls, root, tag, match_id):
        return event_class[tag](root, match_id)


class GoalKeeping(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = tuple(float(p) for p in root.text.split(','))


class GoalAttempt(Event):
    """gmouth_y and gmouth_z are in YZ plane (Z is the height of a shot when crossing the gate line),
    stored in self.yz"""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        coordinates = root.find('coordinates')
        self.start = float(coordinates.attrib['start_x']), float(coordinates.attrib['start_y'])

        gmouth_y = float(coordinates.attrib['gmouth_y']) if coordinates.attrib['gmouth_y'] != "" else None
        gmouth_z = float(coordinates.attrib['gmouth_z']) if coordinates.attrib['gmouth_z'] != "" else None
        self.yz = gmouth_y, gmouth_z

        # if end_x and end_y doesn't exist, it means the shot is off-target.
        self.end = float(coordinates.attrib.get('end_x') or 100.0), float(coordinates.attrib.get('end_y') or gmouth_y)


class ActionArea(Event):
    """It's something like heat map. The id of an action_area indicates the position in the pitch"""
    pass


class HeadedDual(Event):
    """Only reflects the headed duals that a player won, failed will only stored to the counterparty, not current one"""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))
        self.counterparty_id = int(root.find('otherplayer').text)
        # self.counterparty = PlayerPool.get(root.find('otherplayer').text)


class Interception(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))


class Clearance(Event):
    """There's a boolean tag 'headed' to identify whether the clearence is done by head."""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))


class Pass(Event):
    """There's tagging on each pass event, such as long_ball, assist."""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = tuple(float(p) for p in root.find('start').text.split(','))
        self.end = tuple(float(p) for p in root.find('end').text.split(','))


class Tackle(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))
        self.player_id = int(root.find('tackler').text)
        self.counterparty_id = int(root.attrib['player_id'])
        # self.player = PlayerPool.get(root.find('tackler').text)
        # self.counterparty = PlayerPool.get(root.attrib['player_id'])


class Cross(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = tuple(float(p) for p in root.find('start').text.split(','))
        self.end = tuple(float(p) for p in root.find('end').text.split(','))


class Corner(Event):
    """swere could be inward / outward, which means the curve direction of a corner"""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = tuple(float(p) for p in root.find('start').text.split(','))
        self.end = tuple(float(p) for p in root.find('end').text.split(','))


class Offside(Event):
    pass


class KeeperSweeper(Event):
    """KeeperSweeper means the goal keeper proactively runs out of the box."""
    pass


class OneOnOne(Event):
    pass


class SetPiece(Event):
    """Goals that due to SetPiece"""
    pass


class TakeOn(Event):
    """TakeOn means one player takes the ball to pass the defence of another player."""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))


class Foul(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))
        self.counterparty_id = int(root.find('otherplayer').text)
        # self.counterparty = PlayerPool.get(root.find('otherplayer').text)


class Card(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))
        self.card_type = root.find('card').text


class Block(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        if root.find('loc'):
            self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))
        elif root.find('start') and root.find('end'):
            self.start = self.end = tuple(float(p) for p in root.find('end').text.split(','))


class ExtraHeatMap(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))


class BallOut(Event):
    """Ball-Out means a player caused the ball going out of the boundary."""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = tuple(float(p) for p in root.find('start').text.split(','))
        self.end = tuple(float(p) for p in root.find('end').text.split(','))


event_class = {
    'goal_keeping': GoalKeeping,
    'goals_attempts': GoalAttempt,
    'action_areas': ActionArea,
    'headed_duals': HeadedDual,
    'interceptions': Interception,
    'clearances': Clearance,
    'all_passes': Pass,
    'tackles': Tackle,
    'crosses': Cross,
    'corners': Corner,
    'offside': Offside,
    'keepersweeper': KeeperSweeper,
    'oneonones': OneOnOne,
    'setpieces': SetPiece,
    'takeons': TakeOn,
    'fouls': Foul,
    'cards': Card,
    'blocked_events': Block,
    'extra_heat_maps': ExtraHeatMap,
    'balls_out': BallOut
}
