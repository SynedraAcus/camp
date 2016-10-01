"""
Various Listeners that check for win/fail, level switch conditions, achievements and so on
"""

class Listener():
    def process_game_event(self, event):
        raise NotImplementedError('Event listener methods should be overloaded')
