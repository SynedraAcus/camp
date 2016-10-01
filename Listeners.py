"""
Various Listeners that check for win/fail, level switch conditions, achievements and so on
"""
from Actor import Actor
from Controller import PlayerController


class Listener():
    def process_game_event(self, event):
        raise NotImplementedError('Event listener methods should be overloaded')

class DeathListener(Listener):
    def process_game_event(self, event):
        if event.event_type == 'was_destroyed':
            if isinstance(event.actor, Actor) and isinstance(event.actor.controller, PlayerController):
                print('PC was killed. So it goes.')