"""
Component classes that add various functionality to Actors
"""

from random import choice

class Component(object):
    """
    Base class for components.
    Currently only allows component to remember which actor it's attached to.
    """
    def __init__(self):
        self.actor = None

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

class DescriptorComponent(Component):
    """
    The component that contains various data about this actor
    """
    def __init__(self, name='Unnamed actor', description='No description'):
        self.name = name
        self.description = description

    def get_description(self, combat=False):
        """
        Return a string that describes the actor this component is attached to.
        :param combat: boolean. If set to True, combat capabilities of this actor will be returned
        :return:
        """
        r = '{0}\n{1}'.format(self.name, self.description)
        if combat:
            if self.actor.fighter:
                r += '\nThis actor has {0} hp.\nIts attacks are {1}\nIts defenses are {2}'.format(
                    self.actor.fighter.hp,
                    '|'.join((str(x) for x in self.actor.fighter.attacks)),
                    '|'.join((str(x) for x in self.actor.fighter.defenses))
                )
            else:
                raise ValueError('Cannot request combat description from Actor without FighterComponent!')
        return r



class InventoryComponent(Component):
    """
    Component that allows to carry stuff
    """
    pass
