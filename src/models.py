import re
import datetime

import aiomysql

from .settings import logger, CONFIG
from .error import EventGroupNameNotFound


class DBConnection:
    pool = None

    @classmethod
    async def get_pool(cls, event_loop):
        if cls.pool is None:
            cls.pool = await aiomysql.create_pool(host=CONFIG['data_db']['host'], port=CONFIG['data_db']['port'],
                                                  user=CONFIG['data_db']['username'],
                                                  password=CONFIG['data_db']['password'],
                                                  db='squawka', loop=event_loop)
        return cls.pool

    @classmethod
    async def close(cls):
        if cls.pool is not None:
            cls.pool.close()
            await cls.pool.wait_closed()


class DBModel:
    __table_name__ = ''
    __pk__ = []
    __static_fields__ = []
    __references__ = []

    def __getattr__(self, name):
        try:
            obj = eval(f'self.{name[:-2]}')
        except NameError as e:
            raise AttributeError(e)

        if isinstance(obj, Coordinate):
            if name[-2:] in ['_0', '_1']:
                return eval(f'self.{name[:-2]}.x{name[-1:]}')

        return super().__getattr__(name)

    @staticmethod
    def _properize(val):
        if isinstance(val, int) or isinstance(val, float):
            return f"{val}"
        elif isinstance(val, datetime.datetime):
            return f"'{datetime.datetime.strftime(val, '%Y-%m-%d %H:%M:%S')}'"
        else:
            return f"'{val}'"

    def _generate_db_field_names(self, include_pk=True):
        all_field_names = [f'{r}_id' for r in self.__references__] \
                          + self.__static_fields__ \
                          + (self.__pk__ if include_pk else [])
        return ','.join([f'`{f}`' for f in all_field_names])

    def _generate_db_field_values(self, include_pk=True):
        all_field_names = [f'{r}.id' for r in self.__references__] \
                          + self.__static_fields__ \
                          + (self.__pk__ if include_pk else [])
        all_field_values = [self._properize(eval(f'self.{f}')) for f in all_field_names]
        return ','.join(all_field_values)

    def _generate_db_field_name_value_pairs(self, include_pk=True):
        static_field_names = self.__static_fields__ + (self.__pk__ if include_pk else [])
        proper_ref_kv = {f'{f}_id': self._properize(eval(f'self.{f}.id')) for f in self.__references__}
        all_field_kv = {**proper_ref_kv, **{f: self._properize(eval(f'self.{f}')) for f in static_field_names}}
        return ','.join([f"`{k}`={v}" for k, v in all_field_kv.items()])

    async def save(self, loop, include_pk=True):
        """It saves the object into DB by performing an upsert operation."""
        pool = await DBConnection.get_pool(loop)
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                sql = f"INSERT INTO `{self.__table_name__}` ({self._generate_db_field_names(include_pk=include_pk)}) " \
                      f"values ({self._generate_db_field_values(include_pk=include_pk)}) " \
                      f"on duplicate key update {self._generate_db_field_name_value_pairs(False)}"
                logger.debug(sql)
                await cur.execute(sql)
                await conn.commit()


class Coordinate:
    def __init__(self, x0, x1):
        self.x0 = float(x0)
        self.x1 = float(x1)

    def __repr__(self):
        return f'({self.x0}, {self.x1})'


class Player(DBModel):
    __table_name__ = 'player'
    __pk__ = ['id']
    __static_fields__ = ['name', 'date_of_birth', 'weight', 'height', 'country']
    __references__ = []

    def __init__(self, root):
        self.id = int(root.attrib.get('id'))
        self.name = root.find('name').text.strip()
        self.date_of_birth = datetime.datetime.strptime(root.find('dob').text, '%d/%m/%Y')
        self.weight = float(root.find('weight').text) if root.find('weight').text != 'Unknown' else None
        self.height = float(root.find('height').text) if root.find('height').text != 'Unknown' else None
        self.country = root.find('country').text.strip()

    def __repr__(self):
        return f'Player-{self.id}'


class Participant(DBModel):
    __table_name__ = 'participation'
    __pk__ = ['']
    __static_fields__ = ['init_loc_0', 'init_loc_1', 'position', 'team_id']
    __references__ = ['match', 'player']

    """It's different from Player. It stores player info related only to this match, while Player is static."""
    def __init__(self, root, match):
        self.match = match
        self.player = Player(root)
        self.team_id = int(root.attrib.get('team_id'))
        self.init_loc = Coordinate(root.find('x_loc').text, root.find('y_loc').text)
        self.position = root.find('position').text.strip()
        # self.player = PlayerPool.get(root.attrib.get('id'))

    async def _save_players(self, loop):
        await self.player.save(loop)

    async def _save_paticipation(self, loop):
        await super().save(loop, include_pk=False)

    async def save(self, loop):
        await self._save_players(loop)
        await self._save_paticipation(loop)


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


class Team(DBModel):
    __table_name__ = 'team'
    __pk__ = ['id']
    __static_fields__ = ['name', 'short_name']

    def __init__(self, root):
        self.id = int(root.attrib.get('id'))
        self.name = root.find('long_name').text.strip()
        self.short_name = root.find('short_name').text.strip()

    def __repr__(self):
        return f'{self.name} (id: {self.id})'


class Match(DBModel):
    __table_name__ = 'match'
    __pk__ = ['id']
    __static_fields__ = ['league_id', 'kickoff_time', 'stadium', 'summary', 'home_score', 'away_score']
    __references__ = ['home_team', 'away_team']

    def __init__(self, root, league_id, match_id):
        game = root.find('data_panel').find('game')
        teams = list(game.findall('team'))
        self.id = match_id
        self.league_id = league_id
        self.summary = root.find('data_panel').find('system').find('headline').text.strip()
        self.kickoff_time = datetime.datetime.strptime(game.find('kickoff').text, '%a, %d %b %Y %H:%M:%S %z')
        self.stadium = game.find('venue').text.strip()
        self.home_team = Team(teams[0])
        self.away_team = Team(teams[1])

        m = re.search(r'(\d+) - (\d+)', self.summary)
        self.home_score, self.away_score = int(m.group(1)), int(m.group(2))

        # PlayerPool.update(root.find('data_panel').find('players'))
        self.participants = [Participant(p, self) for p in root.find('data_panel').find('players')]
        self.event_groups = [EventGroup(f, self.id) for f in root.find('data_panel').find('filters')]

    def __repr__(self):
        return f'{self.summary}'

    def find_event_group(self, event_group_name):
        for eg in self.event_groups:
            if eg.name == event_group_name:
                return eg
        raise EventGroupNameNotFound(f'Event group name {event_group_name} not found. '
                                     f'Valid event group names are: {[eg.name for eg in self.event_groups]}')

    async def _save_match(self, loop):
        await super().save(loop)

    async def save(self, loop):
        await self.home_team.save(loop)
        await self.away_team.save(loop)
        await self._save_match(loop)
        [await p.save(loop) for p in self.participants]
        # all_events = [e for eg in self.event_groups for e in eg]
        # TODO: insert all_events using insertmany


class EventGroup:
    def __init__(self, root, match_id):
        self.name = root.tag
        self.match_id = match_id
        self.events = [Event.from_element_root(e, root.tag, match_id) for tc in root.findall('time_slice')
                       for e in tc.findall('event')]

    def __iter__(self):
        return (e for e in self.events)

    def __getitem__(self, item):
        return self.events[item]

    def __repr__(self):
        return f'{self.__class__.__name__} ({len(self.events)})'


class Event:
    attr_key_type = {'action_type': str, 'headed': bool, 'mins': int, 'minsec': int, 'player_id': int, 'secs': int,
                     'team_id': int, 'type': str, 'injurytime_play': bool, 'uid': str, 'throw_ins': bool, 'team': int,
                     'other_player': int, 'other_team': int, 'shot_player': int, 'shot_team': int, 'ot_id': int,
                     'ot_outcome': bool, 'gz': float, 'gy': float, 'k': bool, 'a': bool}

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
    stored in self.yz_plane"""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        coordinates = root.find('coordinates')
        self.start = float(coordinates.attrib['start_x']), float(coordinates.attrib['start_y'])

        gmouth_y = float(coordinates.attrib['gmouth_y']) if coordinates.attrib['gmouth_y'] != "" else None
        gmouth_z = float(coordinates.attrib['gmouth_z']) if coordinates.attrib['gmouth_z'] != "" else None
        self.yz_plane_pt = gmouth_y, gmouth_z

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
