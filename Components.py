"""
Component classes that add various functionality to Actors
"""

from random import choice

class Component(object):
    """
    Base class for components.
    Currently does nothing, but may be used later
    """
    pass

class FighterComponent(Component):
    """
    The component that provides the actor with combat capabilities
    """
    def __init__(self, hp=5, attacks=[1, 2, 3], defenses=[0, 0, 1]):
        self.hp = hp
        self.attacks = attacks
        self.defenses = defenses

    def attack(self):
        return choice(self.attacks)

    def defense(self):
        return choice(self.defenses)

class InventoryComponent(Component):
    """
    Component that allows to carry stuff
    """
    pass
