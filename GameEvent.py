"""
GameEvent base class
"""

class GameEvent(object):
    """
    Something that has happened in the game.
    Contrary to its name, this is not an event in IO/clock sense. This is, rather, a data class that contains a
    pointer to actor involved, location(s) of the event and event type. The latter must be an str and its value
    should be one of GameEvent.acceptable_types elements
    Actor and location can be omitted for some event types. If actor is provided and location is not, it is
    assumed to be actor's location
    """
    acceptable_types = ('moved',
                        'was_destroyed',
                        'attacked',
                        'log_updated',
                        'picked_up',
                        'dropped',
                        'actor_spawned',
                        'construction_spawned',
                        'exploded',
                        'shot')

    def __init__(self, event_type=None, actor=None, location=None):
        assert isinstance(event_type, str) and event_type in self.acceptable_types
        self.event_type = event_type
        self.actor = actor
        if location:
            self.location = location
        elif self.actor:
            self.location = actor.location