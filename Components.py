"""
Component classes that add various functionality to Actors
"""

from random import choice
from Items import Item
from GameEvent import GameEvent


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
    def __init__(self, max_hp=5, attacks=(1, 2, 3), defenses=(0, 0, 1), **kwargs):
        super(FighterComponent, self).__init__(**kwargs)
        self.max_hp = max_hp
        self._hp = max_hp
        self.attacks = attacks
        self.defenses = defenses

    def get_damaged(self, attack=0):
        """
        Be attacked for 'attack' damage, dying if necessary. Defense, if any, is applied.
        :param attack: int
        :return:
        """
        damage = attack - self.defense()
        if damage > 0:
            self.actor.map.extend_log('{0} was hit for {1} damage'.format(self.actor.descriptor.name,
                                                                          damage))
        else:
            self.actor.map.extend_log('{0} managed to evade the blow'.format(self.actor.descriptor.name))
        self.hp -= damage
        if self.hp <= 0:
            if self.actor.inventory and len(self.actor.inventory) > 0:
                if not self.actor.map.get_item(location=self.actor.location,
                                               layer='items'):
                    self.actor.drop_item(0)
            self.actor.map.extend_log('{0} was killed'.format(self.actor.descriptor.name))
            self.actor.map.delete_item(location=self.actor.location, layer=self.actor.layer)
            #  Layer is not hardcoded because there are Fighter Constructions
            #  Actor and Component should be garbage collected after this event fires, as there are no more
            #  references to them besides the event
            self.actor.map.game_events.append(GameEvent(event_type='was_destroyed',
                                                        actor=self.actor))

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, hp):
        #  Only checking for HP overflow. Underflow (ie death) is covered by self.get_damaged
        if hp > self.max_hp:
            self._hp = self.max_hp
        else:
            self._hp = hp

    def attack(self):
        return choice(self.attacks)

    def defense(self):
        return choice(self.defenses)


class DescriptorComponent(Component):
    """
    The component that contains various displayable data about this actor
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
        self.volume = volume  #  Inventories of more than ten slots not supported by the interface
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

    def __len__(self):
        return len(self.items)

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
            return True
        else:
            return False
