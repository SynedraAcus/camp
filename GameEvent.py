"""
GameEvent base class and the event queue
"""
from collections import deque

class GameEvent:
    """
    Something that has happened in the game.
    Contrary to its name, this is not an event in IO/clock sense. This is, rather, a data class that contains a
    pointer to actor involved, location(s) of the event and event type. The latter must be an str and its value
    should be one of GameEvent.acceptable_types elements
    Actor and location can be omitted for some event types. If actor is provided and location is not, it is
    assumed to be actor's location
    """
    acceptable_types = {'moved',
                        'was_destroyed',
                        'attacked',
                        'log_updated',
                        'picked_up',
                        'dropped',
                        'actor_spawned',
                        'construction_spawned',
                        'exploded',
                        'shot',
                        'rocket_shot',
                        'hp_changed',
                        'ammo_changed',
                        'inventory_updated',
                        'queue_exhausted'}

    def __init__(self, event_type=None, actor=None, location=None):
        assert isinstance(event_type, str) and event_type in self.acceptable_types
        self.event_type = event_type
        self.actor = actor
        if location:
            self.location = location
        elif self.actor:
            self.location = actor.location


class EventQueue:
    """
    Event queue. Currently a wrapper around a standard collections.deque
    """
    def __init__(self):
        self._deque = deque()
        self.listeners = []

    def append(self, item):
        """
        Push a GameEvent to the queue
        :param item: GameEvent to add
        :return:
        """
        if not isinstance(item, GameEvent):
            raise ValueError('Only GameEvents can be pushed to the event queue')
        self._deque.append(item)

    def clear(self):
        """
        Remove all elements from EventQueue leaving it with length 0
        :return:
        """
        self._deque.clear()

    def popleft(self):
        """
        Pop a GameEvent from the queue start
        :return: GameEvent
        """
        return self._deque.popleft()

    def pop(self):
        """
        Pop a GameEvent
        :return:
        """
        return self._deque.pop()

    def register_listener(self, listener):
        """
        :param listener:
        :return:
        Register some object as a listener. Its' process_game_event() will be called in every
        pass_event() with the event.
        """
        if hasattr(listener, 'process_game_event'):
            self.listeners.append(listener)
        else:
            raise AttributeError('Listener doesn\'t have process_game_event() method')

    def unregister_listener(self, listener):
        """
        Forget a single listener.
        This method should be called when a listener is being destroyed. Otherwise it will be retained in
        this queue's `listeners` and thus will not be garbage collected
        :param listener:
        :return:
        """
        self.listeners.remove(listener)

    def pass_event(self):
        """
        Pop a single event from the queue and pass it to all listeners
        :return:
        """
        e = self.popleft()
        for listener in self.listeners:
            listener.process_game_event(e)

    def pass_all_events(self):
        """
        Pass all the events in the queue to listeners. In addition, passes a special `queue_exhausted` event
        that signalises that that's it for now. It allows eg animation system to start animating turn
        :return:
        """
        self.append(GameEvent(event_type='queue_exhausted'))
        while len(self._deque) > 0:
            self.pass_event()
