"""
Construction classes. All the stuff here is to be placed at 'constructions' layer.
A construction is, basically, a sort of Actor: it can make turn, it have components,
it can be collided into. The reason to have a separate layer is that only one actor
may be present at a cell at a time, but there may be both actor and construction.
Typical constructions are immobile interactive stuff: traps, chests, stairs and such.
"""

from MapItem import MapItem
from Actor import Actor, GameEvent
from Controller import AIController
from Components import FighterComponent, DescriptorComponent

class Construction(MapItem):
    """
    Base constructor class. Registers fighter, descriptor, controller and inventory components, if such are
    provided to constructor. Pretty similar to Actor.
    """
    def __init__(self,
                 image_source = 'DownStairs.png',
                 fighter = None,
                 descriptor = None,
                 inventory = None,
                 controller = None,
                 **kwargs):
        super(Construction, self).__init__(**kwargs)
        #  Components
        self.fighter = fighter
        self.descriptor = descriptor
        self.inventory = inventory
        self.controller = controller
        #  Image
        self.image_source = image_source
        #  These are to be set by self.connect_to_map
        self.map = None
        self.location = None
        self.layer = None

    def make_turn(self):
        pass

    def connect_to_map(self, layer='constructions', map=None, location=None):
        """
        Remember own position on map (and map itself)
        :param layer:
        :param map:
        :param location:
        :return:
        """
        self.map = map
        self.layer = layer
        self.location = location

class Spawner(Construction):
    """
    A construction that spawns enemies every few turns
    """
    def __init__(self, spawn_frequency=5, **kwargs):
        super(Spawner, self).__init__(**kwargs)
        self.spawn_frequency = spawn_frequency
        self.spawn_counter = 1

    def make_turn(self):
        if self.spawn_counter < self.spawn_frequency:
            self.spawn_counter += 1
        else:
            self.spawn_counter = 1
            if not self.map.get_item(location=self.location,
                                     layer='actors'):
                #  Only spawn if the tile is empty
                baby = Actor(player=False, controller=AIController(), fighter=FighterComponent(),
                             descriptor=DescriptorComponent(name='NPC2'),
                             image_source='NPC.png')
                self.map.add_item(item=baby, location=self.location, layer='actors')
                self.map.game_events.append(GameEvent(event_type='spawned', location=self.location,
                                                      actor=baby))