import re
import asyncio
import datetime

import aiomysql

from .settings import logger, CONFIG
from .error import EventGroupNameNotFound
from .utils import flatten


class DBConnection:
    _pool = None

    @classmethod
    async def get_pool(cls, event_loop):
        if cls._pool is None:
            cls._pool = await aiomysql.create_pool(host=CONFIG['data_db']['host'], port=CONFIG['data_db']['port'],
                                                   user=CONFIG['data_db']['username'],
                                                   password=CONFIG['data_db']['password'],
                                                   db='squawka', maxsize=50, loop=event_loop)
        return cls._pool

    @classmethod
    async def close(cls):
        if cls._pool is not None:
            cls._pool.close()
            await cls._pool.wait_closed()


class DBModel:
    __table_name__ = ''
    __pk__ = []
    __static_fields__ = []

    def __getattr__(self, name):
        # Deal with field of type Coordinate
        if name[-2:] in ['_0', '_1']:
            if hasattr(self, name[:-2]):
                if isinstance(getattr(self, name[:-2]), Coordinate):
                    return getattr(self, name[:-2]).x[int(name[-1:])]

        # Deal with field which is actually a reference to another DBModel object
        if name[-3:] == '_id':
            if hasattr(self, name[:-3]):
                if isinstance(getattr(self, name[:-3]), DBModel):
                    return getattr(self, name[:-3]).id

    @staticmethod
    def _properize(val):
        if isinstance(val, int) or isinstance(val, float):
            return f"{val}"
        elif isinstance(val, datetime.datetime):
            return f"'{datetime.datetime.strftime(val, '%Y-%m-%d %H:%M:%S')}'"
        else:
            return f"'{val}'"

    def _get_field_name_value_pairs(self, static_fields, pk, id_auto_increment):
        all_cols = set(static_fields + pk) - ({'id'} if id_auto_increment else set())
        return {f: self._properize(getattr(self, f)) for f in all_cols}

    async def save(self, loop, static_fields=None, pk=None, id_auto_increment=False):
        """It saves the object into DB by performing an upsert operation."""
        static_fields = static_fields or self.__static_fields__
        pk = pk or self.__pk__
        pool = await DBConnection.get_pool(loop)
        logger.debug(f'id(pool)={id(pool)}, pool.size={pool.size}, pool.freesize={pool.freesize}')
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                pairs = self._get_field_name_value_pairs(static_fields, pk, id_auto_increment)
                col_names = ','.join([f'`{k}`' for k in pairs.keys()])
                col_values = ','.join([v for v in pairs.values()])
                col_name_values = ','.join([f'`{k}`={v}' for k, v in pairs.items() if k not in pk])
                sql = f"INSERT INTO `{self.__table_name__}` ({col_names}) " \
                      f"values ({col_values}) " \
                      f"on duplicate key update {col_name_values}"
                logger.debug(sql)
                await cur.execute(sql)
                await conn.commit()


class Coordinate:
    def __init__(self, x0, x1):
        self.x = None if x0 is None else float(x0), None if x1 is None else float(x1)

    def __repr__(self):
        return f'({self.x[0]}, {self.x[1]})'


class Player(DBModel):
    __table_name__ = 'player'
    __pk__ = ['id']
    __static_fields__ = ['name', 'date_of_birth', 'weight', 'height', 'country']

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
    __pk__ = ['player_id', 'match_id', 'team_id']
    __static_fields__ = ['init_loc_0', 'init_loc_1', 'position']

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
        await super().save(loop)

    async def save(self, loop, static_fields=None, pk=None, id_auto_increment=False):
        await self._save_players(loop)
        await self._save_paticipation(loop)


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
    __static_fields__ = ['url', 'league_id', 'kickoff_time', 'stadium', 'summary', 'home_score', 'away_score',
                         'home_team_id', 'away_team_id']

    def __init__(self, url, root, league_id, match_id):
        self.url = url
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
        return f'{self.summary} (id: {self.id})'

    def find_event_group(self, event_group_name):
        for eg in self.event_groups:
            if eg.name == event_group_name:
                return eg
        raise EventGroupNameNotFound(f'Event group name {event_group_name} not found. '
                                     f'Valid event group names are: {[eg.name for eg in self.event_groups]}')

    async def exists_in_db(self, loop):
        pool = await DBConnection.get_pool(loop)
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(f"SELECT COUNT(*) as cnt FROM `{self.__table_name__}` WHERE `id`={self.id}")
                r, = await cur.fetchone()
                return r > 0

    async def _save_match(self, loop):
        await super().save(loop)

    async def save(self, loop, static_fields=None, pk=None, id_auto_increment=False):
        exists = await self.exists_in_db(loop)
        if not exists:
            tasks = [self.home_team.save(loop), self.away_team.save(loop), self._save_match(loop)] \
                    + [p.save(loop) for p in self.participants] \
                    + [e.save(loop) for eg in self.event_groups for e in eg]
            await asyncio.wait(tasks)
        else:
            logger.info('Match <<< {} >>> already exists in DB.'.format(self))


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


class Event(DBModel):
    __table_name__ = 'event'
    __pk__ = ['id']

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

    async def save(self, loop, static_fields=None, pk=None, id_auto_increment=False):
        controlled = [k for k in self.__dict__.keys() if k in controlled_event_cols]
        coord_fields = flatten([[f'{f}_0', f'{f}_1'] for f in controlled if isinstance(getattr(self, f), Coordinate)])
        non_coord_fields = [f for f in controlled if not isinstance(getattr(self, f), Coordinate)]
        static_fields = [f for f in coord_fields + non_coord_fields if getattr(self, f) is not None]
        await super().save(loop, static_fields=static_fields, id_auto_increment=True)


class GoalKeeping(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = Coordinate(*(p for p in root.text.split(',')))


class GoalAttempt(Event):
    """gmouth_y and gmouth_z are in YZ plane (Z is the height of a shot when crossing the gate line),
    stored in self.yz_plane"""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        coordinates = root.find('coordinates')
        self.start = Coordinate(coordinates.attrib['start_x'], coordinates.attrib['start_y'])

        gmouth_y = float(coordinates.attrib['gmouth_y']) if coordinates.attrib['gmouth_y'] != "" else None
        gmouth_z = float(coordinates.attrib['gmouth_z']) if coordinates.attrib['gmouth_z'] != "" else None
        self.yz_plane_coord = Coordinate(gmouth_y, gmouth_z)

        # if end_x and end_y doesn't exist, it means the shot is off-target.
        self.end = Coordinate(coordinates.attrib.get('end_x') or 100.0, coordinates.attrib.get('end_y') or gmouth_y)


class ActionArea(Event):
    """It's something like heat map. The id of an action_area indicates the position in the pitch"""
    pass


class HeadedDual(Event):
    """Only reflects the headed duals that a player won, failed will only stored to the counterparty, not current one"""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = Coordinate(*(p for p in root.find('loc').text.split(',')))
        self.counterparty_id = int(root.find('otherplayer').text)
        # self.counterparty = PlayerPool.get(root.find('otherplayer').text)


class Interception(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = Coordinate(*(p for p in root.find('loc').text.split(',')))


class Clearance(Event):
    """There's a boolean tag 'headed' to identify whether the clearence is done by head."""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = Coordinate(*(p for p in root.find('loc').text.split(',')))


class Pass(Event):
    """There's tagging on each pass event, such as long_ball, assist."""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = Coordinate(*(p for p in root.find('start').text.split(',')))
        self.end = Coordinate(*(p for p in root.find('end').text.split(',')))


class Tackle(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = Coordinate(*(p for p in root.find('loc').text.split(',')))
        self.player_id = int(root.find('tackler').text)
        self.counterparty_id = int(root.attrib['player_id'])
        # self.player = PlayerPool.get(root.find('tackler').text)
        # self.counterparty = PlayerPool.get(root.attrib['player_id'])


class Cross(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = Coordinate(*(p for p in root.find('start').text.split(',')))
        self.end = Coordinate(*(p for p in root.find('end').text.split(',')))


class Corner(Event):
    """swere could be inward / outward, which means the curve direction of a corner"""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = Coordinate(*(p for p in root.find('start').text.split(',')))
        self.end = Coordinate(*(p for p in root.find('end').text.split(',')))


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
        self.start = self.end = Coordinate(*(p for p in root.find('loc').text.split(',')))


class Foul(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = Coordinate(*(p for p in root.find('loc').text.split(',')))
        self.counterparty_id = int(root.find('otherplayer').text)
        # self.counterparty = PlayerPool.get(root.find('otherplayer').text)


class Card(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = Coordinate(*(p for p in root.find('loc').text.split(',')))
        self.card_type = root.find('card').text


class Block(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        if root.find('loc'):
            self.start = self.end = Coordinate(*(p for p in root.find('loc').text.split(',')))
        elif root.find('start') and root.find('end'):
            self.start = self.end = Coordinate(*(p for p in root.find('end').text.split(',')))


class ExtraHeatMap(Event):
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = self.end = Coordinate(*(p for p in root.find('loc').text.split(',')))


class BallOut(Event):
    """Ball-Out means a player caused the ball going out of the boundary."""
    def __init__(self, root, match_id):
        super().__init__(root, match_id)
        self.start = Coordinate(*(p for p in root.find('start').text.split(',')))
        self.end = Coordinate(*(p for p in root.find('end').text.split(',')))


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

controlled_event_cols = ['player_id', 'counterparty_id', 'match_id', 'minsec', 'event_type', 'start', 'end',
                         'yz_plane_coord', 'a', 'action_type', 'card_type', 'gy', 'gz', 'headed', 'injurytime_play', 'k',
                         'ot_id', 'ot_outcome', 'throw_ins', 'type', 'uid']
