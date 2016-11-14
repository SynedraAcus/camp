"""
Various Listeners that check for win/fail, level switch conditions, achievements and so on
"""
from Actor import Actor
from Controller import PlayerController


class Listener():
    def __init__(self):
        self.game_manager = None

    def process_game_event(self, event):
        raise NotImplementedError('Event listener methods should be overloaded')


class DeathListener(Listener):
    """
    A listener that checks for PC death and reports it to the console
    """
    def __init__(self):
        super(DeathListener, self).__init__()

    def process_game_event(self, event):
        if event.event_type == 'was_destroyed':
            if isinstance(event.actor, Actor) and isinstance(event.actor.controller, PlayerController):
                print('PC was killed. So it goes.')


class BorderWalkListener(Listener):
    """
    A Listener that tells GameManager to switch the map whenever player walks on one of the border tiles
    """
    def process_game_event(self, event):
        if event.event_type == 'moved':
            if isinstance(event.actor, Actor) and isinstance(event.actor.controller, PlayerController):
                if event.actor.location[0] == 0:
                    self.game_manager.switch_map(self.game_manager.map.neighbour_maps['west'],
                                                 entrance_direction='west')
                elif event.actor.location[0] == self.game_manager.map.size[0] - 1:
                    self.game_manager.switch_map(self.game_manager.map.neighbour_maps['east'],
                                                 entrance_direction='east')
                elif event.actor.location[1] == 0:
                    self.game_manager.switch_map(self.game_manager.map.neighbour_maps['south'],
                                                 entrance_direction='north')
                elif event.actor.location[1] == self.game_manager.map.size[1] - 1:
                    self.game_manager.switch_map(self.game_manager.map.neighbour_maps['north'],
                                                 entrance_direction='south')

class MapChangeListener(Listener):
    """
    A test Listener that switches map to 'empty' if player moves to the bottom row of the map
    """
    def process_game_event(self, event):
        if event.event_type == 'moved':
            if isinstance(event.actor, Actor) and isinstance(event.actor.controller, PlayerController)\
                        and event.actor.location[1] <= 1:
                self.game_manager.switch_map('empty')