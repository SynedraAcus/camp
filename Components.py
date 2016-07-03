"""
Component classes that add various functionality to Actors
"""

from random import choice
from Items import Item

class Component(object):
    """
    Base class for components.
    Currently only defines actor attribute.
    """
    def __init__(self):
        self.actor = None

class FighterComponent(Component):
    """
    The component that provides the actor with combat capabilities
    """
    def __init__(self, hp=5, attacks=[1, 2, 3], defenses=[0, 0, 1], **kwargs):
        super(FighterComponent, self).__init__(**kwargs)
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
    def __init__(self, name='Unnamed actor', description='No description', **kwargs):
        super(DescriptorComponent, self).__init__(**kwargs)
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
                r += '\nThis Actor has {0} hp.\nIts attacks are {1}\nIts defenses are {2}'.format(
                    self.actor.fighter.hp,
                    '|'.join((str(x) for x in self.actor.fighter.attacks)),
                    '|'.join((str(x) for x in self.actor.fighter.defenses))
                )
            else:
                raise ValueError('Cannot request combat description from Actor without FighterComponent!')
        return r



class InventoryComponent(Component):
    """
    Component that allows Actor to carry stuff
    """
    def __init__(self, volume=10, initial_items=[], **kwargs):
        super(InventoryComponent, self).__init__(**kwargs)
        self.volume = volume #  Inventories of more than ten slots not supported by the interface
        self.items = []
        self.actor = None
        for a in initial_items:
            self.append(a)


    #  List-like behaviour

    def __getitem__(self, item):
        return self.items[item]

    def append(self, item):
        """
        Add a single item to the inventory
        :param item: instance of the Item subclass
        :return:
        """
        assert isinstance(item, Item)
        if len(self.items) < self.volume:
            item.owner = self
            self.items.append(item)
            return True
        else:
            return False

    def remove(self, item):
        """
        Remove a single item from the inventory
        :param item: instance of the Item subclass
        :return:
        """
        #  Let list raise exceptions, if needed
        item.owner = None
        self.items.remove(item)

    def get_string(self):
        """
        Get a string representation of inventory
        :return:
        """
        r = ''
        if len(self.items) == 0:
            r = 'Inventory is empty'
        else:
            for i in range(0, len(self.items)):
                r += '{0} - {1}\n'.format(i, self.items[i].name)
        return r

class FactionComponent(Component):
    """
    A component that is responsible for (N)PC relationships. Actors with the same
    faction do not attack each other (and maybe even help, if they are able),
    and there may be interparty peace treaties and allies and stuff
    """
    def __init__(self, faction=None, enemies=[], allies=[], **kwargs):
        super(FactionComponent, self).__init__(**kwargs)
        self.faction = faction
        self.enemies = enemies
        self.allies = allies

    def is_friendly(self, other):
        """
        Return True if other faction is a friend and should be supported
        :param other: FactionComponent
        :return:
        """
        if other.faction == self.faction or other.faction in self.allies:
            return True
        else:
            return False

    def is_enemy(self, other):
        """
        Return True if other faction is an enemy and should be attacked
        :param other: FactionComponent
        :return:
        """
        if other.faction in self.enemies:
            print(self.enemies)
            return True
        else:
            return False
