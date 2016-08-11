"""
Item and Effect classes and their subclasses.
"""

from Actor import GameEvent
from MapItem import MapItem
from random import random, choice

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
    def __init__(self, map=None, **kwargs):
        super(TileTargetedEffect, self).__init__(**kwargs)

    def affect(self, map, location):
        if self.effect_type == 'spawn_construction':
            #  Spawn something in construction layer unless there already is something
            if not map.get_item(location=location, layer='constructions'):
                map.add_item(item=self.effect_value, location=location, layer='constructions')
                map.game_events.append(GameEvent(event_type='construction_spawned',
                                                 actor=self.effect_value,
                                                 location=location))
                return True
            else:
                return False
        elif self.effect_type == 'explode':
            #  Blow up, dealing effect_value damage to all fighters on this and neighbouring tiles and
            #  destroying items with 50% chance
            map.game_events.append(GameEvent(event_type='exploded', location=location))
            destroyed_items = False
            for tile in map.get_neighbour_coordinates(location=location, return_query=True):
                for victim in map.get_column(tile):
                    if hasattr(victim, 'fighter') and victim.fighter:
                        victim.fighter.get_damaged(self.effect_value)
                    elif isinstance(victim, Item) and random() > 0.5:
                        map.delete_item(layer='items', location=tile)
                        map.game_events.append(GameEvent(event_type='was_destroyed',
                                                              actor=victim, location=tile))
                        destroyed_items = True
            if destroyed_items:
                map.extend_log('Some items were destroyed')
            return True


class Item(MapItem):
    """
    Base class for the inventory item. Inherits from MapItem to allow placing items on map.
    """
    def __init__(self, name='Item', image_source='Bottle.png', owner=None, descriptor=None, **kwargs):
        super(Item, self).__init__(**kwargs)
        #  Owner is an inventory component, not an actor
        self.owner = owner
        self.descriptor = descriptor
        if self.descriptor:
            self.descriptor.actor = self
        self.image_source = image_source

    @property
    def name(self):
        return self.descriptor.name

    @name.setter
    def name(self, value):
        self.descriptor.name = value

    def use(self):
        """
        This method uses the item. It should be overridden in child classes.
        The override should return True upon successfully using an item
        :return:
        """
        raise NotImplementedError('use should be overloaded in Item\'s child')


class PotionTypeItem(Item):
    """
    Single-use items that affect whoever uses them and vanishes.
    When creating object, it should be supplied with the Effect class instance that
    can affect Actor class.
    """
    def __init__(self, effect=lambda a: None, **kwargs):
        super(PotionTypeItem, self).__init__(**kwargs)
        self.effect = effect

    def use(self, target=None):
        """
        Spend this item: apply effect, remove it from inventory and send a message to game log
        Returns True if using item was possible (not necessary successful!)
        :param target: type depends on Effect class and may be Actor, location or whatever else subclass supports
        :return:
        """
        self.owner.actor.map.extend_log('{0} used {1}'.format(self.owner.actor.descriptor.name,
                                                                  self.name))
        if isinstance(self.effect, FighterTargetedEffect):
            if not target:
                r = self.effect.affect(self.owner.actor)
            else:
                r = self.effect.affect(target)
        elif isinstance(self.effect, TileTargetedEffect):
            if not target:
                if self.effect.effect_type not in 'explode':
                    r = self.effect.affect(self.owner.actor.map, self.owner.actor.location)
                else:
                    self.owner.actor.map.extend_log('Better not to blow yourself up. Use [F]ire command.')
                    r = False
            else:
                r = self.effect.affect(self.owner.actor.map, target)
        #  Log usage and return result
        if r:
            self.owner.remove(self)
            return True
        else:
            return False

