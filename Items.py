"""
Item classes for the stuff that may be put in the inventories
"""

from MapItem import MapItem
from Effects import FighterTargetedEffect, TileTargetedEffect
from Components import *


class Item(MapItem):
    """
    Base class for the inventory item. Inherits from MapItem to allow placing items on map.
    """
    def __init__(self, name='Item', image_source='Bottle.png', owner=None, **kwargs):
        super(Item, self).__init__(**kwargs)
        self.name = name
        #  Owner is an inventory component, not an actor
        self.owner = owner

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

    def use(self):
        """
        Spend this item: apply effect, remove it from inventory and send a message to game log
        Returns True if using item was possible (not necessary successful!)
        :return:
        """
        #  Use effect on an appropriate target
        if isinstance(self.effect, FighterTargetedEffect):
            r = self.effect.affect(self.owner.actor)
        elif isinstance(self.effect, TileTargetedEffect):
            r = self.effect.affect(self.owner.actor.location)
        #  Log usage and return result
        if r:
            self.owner.actor.map.extend_log('{0} used {1}'.format(self.owner.actor.descriptor.name,
                                                                  self.name))
            self.owner.remove(self)
            return True
        else:
            return False

