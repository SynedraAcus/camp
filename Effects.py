"""
Various effects for potions, spells, events and so on
"""

from Actor import GameEvent
from random import choice

class Effect(object):
    """
    Root effect class
    """
    def __init__(self, effect_type, effect_value):
        self.effect_type = effect_type
        self.effect_value = effect_value


class FighterTargetedEffect(Effect):
    """
    Effect that affects the FighterComponent of an Actor
    """
    def __init__(self, **kwargs):
        super(FighterTargetedEffect, self).__init__(**kwargs)

    def affect(self, actor):
        if self.effect_type == 'heal':
            actor.fighter.hp += choice(self.effect_value)
            return True


class TileTargetedEffect(Effect):
    """
    Effect that affects map tile
    """
    def __init__(self, map, **kwargs):
        super(TileTargetedEffect, self).__init__(**kwargs)
        self.map = map

    def affect(self, location):
        if self.effect_type == 'spawn_construction':
            #  Spawn something in construction layer unless there already is something
            if not self.map.get_item(location=location, layer='constructions'):
                self.map.add_item(item=self.effect_value, location=location, layer='constructions')
                self.map.game_events.append(GameEvent(event_type='construction_spawned',
                                                      actor=self.effect_value,
                                                      location=location))
                return True
            else:
                return False
