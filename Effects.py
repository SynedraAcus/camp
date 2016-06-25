"""
Various effects for potions, spells, events and so on
"""

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