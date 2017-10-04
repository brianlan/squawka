from aiohttp import ClientSession

from .settings import logger


class Player:
    def __init__(self, player_id):
        if isinstance(player_id, str):
            player_id = int(player_id)
        self.id = player_id

    def __repr__(self):
        return f'Player-{self.id}'


class Match:
    def __init__(self, root):
        self.root = root
        self.event_groups = {f.tag: EventGroup(f) for f in root.find('data_panel').find('filters')}


class EventGroup:
    def __init__(self, root):
        self.root = root
        self.events = [Event.from_element_root(e, root.tag) for tc in root.findall('time_slice')
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

    def __init__(self, root):
        self.root = root
        self.counterparty = None
        for k, v in root.items():
            try:
                setattr(self, k, self.attr_key_type[k](v))
            except KeyError as e:
                logger.warn('Type of attr-key {} not been set yet, use str instead. err_msg: {}'.format(k, e))
                setattr(self, k, v)

    def __setattr__(self, key, value):
        if key == 'player_id':
            super().__setattr__('player', Player(value))
        elif key == 'other_player':
            super().__setattr__('counterparty', Player(value))
        else:
            super().__setattr__(key, value)

    @classmethod
    def from_element_root(cls, root, tag):
        return event_class[tag](root)


class GoalKeeping(Event):
    def __init__(self, root):
        super().__init__(root)
        self.start = self.end = tuple(float(p) for p in root.text.split(','))


class GoalAttempt(Event):
    def __init__(self, root):
        super().__init__(root)
        self.start = tuple(float(p) for p in root.find('start').text.split(','))
        self.end = tuple(float(p) for p in root.find('end').text.split(','))


class ActionArea(Event):
    """It's something like heat map. The id of an action_area indicates the position in the pitch"""
    pass


class HeadedDual(Event):
    def __init__(self, root):
        super().__init__(root)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))
        self.counterparty = Player(root.find('otherplayer').text)


class Interception(Event):
    def __init__(self, root):
        super().__init__(root)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))


class Clearance(Event):
    """There's a boolean tag 'headed' to identify whether the clearence is done by head."""
    def __init__(self, root):
        super().__init__(root)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))


class Pass(Event):
    """There's tagging on each pass event, such as long_ball, assist."""
    def __init__(self, root):
        super().__init__(root)
        self.start = tuple(float(p) for p in root.find('start').text.split(','))
        self.end = tuple(float(p) for p in root.find('end').text.split(','))

    def __repr__(self):
        return f'[{self.mins}:{self.secs}] {self.player} passed {self.start} -> {self.end}'


class Tackle(Event):
    def __init__(self, root):
        super().__init__(root)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))
        self.counterparty = Player(root.find('tackler').text)


class Cross(Event):
    def __init__(self, root):
        super().__init__(root)
        self.start = tuple(float(p) for p in root.find('start').text.split(','))
        self.end = tuple(float(p) for p in root.find('end').text.split(','))


class Corner(Event):
    """swere could be inward / outward, which means the curve direction of a corner"""
    def __init__(self, root):
        super().__init__(root)
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
    def __init__(self, root):
        super().__init__(root)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))


class Foul(Event):
    def __init__(self, root):
        super().__init__(root)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))
        self.counterparty = Player(root.find('otherplayer').text)


class Card(Event):
    def __init__(self, root):
        super().__init__(root)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))
        self.card_type = root.find('card').text


class Block(Event):
    def __init__(self, root):
        super().__init__(root)
        if root.find('loc'):
            self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))
        elif root.find('start') and root.find('end'):
            self.start = self.end = tuple(float(p) for p in root.find('end').text.split(','))


class ExtraHeatMap(Event):
    def __init__(self, root):
        super().__init__(root)
        self.start = self.end = tuple(float(p) for p in root.find('loc').text.split(','))


class BallOut(Event):
    """Ball-Out means a player caused the ball going out of the boundary."""
    def __init__(self, root):
        super().__init__(root)
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
