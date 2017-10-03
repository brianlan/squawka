from aiohttp import ClientSession


class Match:
    def __init__(self, root):
        self.root = root
        self.event_groups = [EventGroup(f) for f in root.find('data_panel').find('filters')]


class EventGroup:
    def __init__(self, root):
        self.root = root
        self.events = [Event.from_element_root(e, root.tag) for tc in root.findall('time_slice') for e in tc]


class Event:
    def __init__(self, element_root):
        self.root = element_root

    @classmethod
    def from_element_root(cls, root, tag):
        return event_class[tag](root)


class GoalKeeping(Event):
    pass


class GoalAttempt(Event):
    pass


class ActionArea(Event):
    """It's something like heat map. The id of an action_area indicates the position in the pitch"""
    pass


class HeadedDual(Event):
    pass


class Interception(Event):
    pass


class Clearance(Event):
    pass


class Pass(Event):
    pass


class Tackle(Event):
    pass


class Cross(Event):
    pass


class Corner(Event):
    pass


class Offside(Event):
    pass


class KeeperSweeper(Event):
    pass


class OneOnOne(Event):
    pass


class SetPiece(Event):
    pass


class TakeOn(Event):
    pass


class Foul(Event):
    pass


class Card(Event):
    pass


class Block(Event):
    pass


class ExtraHeatMap(Event):
    pass


class BallOut(Event):
    pass


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


async def process_entry_page(url):
    pass


async def process_match(url):
    pass
