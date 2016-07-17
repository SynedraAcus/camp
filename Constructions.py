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
from copy import deepcopy

class Construction(MapItem):
    """
    Base constructor class. Registers fighter, descriptor, controller and inventory components, if such are
    provided to constructor. Pretty similar to Actor.
    """
    def __init__(self,
                 image_source='DownStairs.png',
                 fighter=None,
                 descriptor=None,
                 inventory=None,
                 controller=None,
                 faction=None,
                 **kwargs):
        super(Construction, self).__init__(**kwargs)
        #  Components
        self.fighter = fighter
        if self.fighter:
            self.fighter.actor = self
        self.descriptor = descriptor
        if self.descriptor:
            self.descriptor.actor = self
        self.inventory = inventory
        if self.inventory:
            self.inventory.actor = self
        self.controller = controller
        if self.controller:
            self.controller.actor = self
        self.faction = faction
        #  Image
        self.image_source = image_source
        #  These are to be set by self.connect_to_map
        self.map = None
        self.location = None
        self.layer = None

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

    def collide(self, other):
        """ Collision callback: get bumped into by some other actor.
        :param other: Actor
        :return:
        """
        if self.fighter and other.fighter:
            #  Process melee attack
            self.map.game_events.append(GameEvent(event_type='attacked',
                                                  actor=other, location=self.location))
            self.fighter.get_damaged(other.fighter.attack())
            #  Collision did happen and take colliding actor's turn, whether it damaged target or not
            return True

    def make_turn(self):
        pass


class Spawner(Construction):
    """
    A construction that spawns enemies every few turns
    """
    def __init__(self, spawn_frequency=5, spawn_factory=None, **kwargs):
        super(Spawner, self).__init__(**kwargs)
        self.spawn_frequency = spawn_frequency
        self.spawn_counter = 1
        self.spawn_factory = spawn_factory

    def make_turn(self):
        if self.spawn_counter < self.spawn_frequency:
            self.spawn_counter += 1
        else:
            self.spawn_counter = 1
            if not self.map.get_item(location=self.location,
                                     layer='actors'):
                #  Only spawn if the tile is empty
                # baby = Actor(player=False, controller=AIController(), fighter=FighterComponent(),
                #              descriptor=DescriptorComponent(name='NPC2'), faction=self.faction,
                #              image_source='NPC.png')
                baby = self.spawn_factory.create_thug()
                self.map.add_item(item=baby, location=self.location, layer='actors')
                self.map.game_events.append(GameEvent(event_type='actor_spawned', location=self.location,
                                                      actor=baby))

class FighterConstruction(Construction):
    """
    Melee fighter construction. Supports 'move' method to enable melee combat
    """
    def make_turn(self):
        self.controller.choose_actor_action()
        self.controller.call_actor_method()

    def move(self, location=(None, None)):
        """
        Move self to a location. Returns True after a successful movement
        and False if it turns out to be impossible. Movement is considered successful if
        collision occured even if the actor didn't actually move.
        :param location: tuple
        :return: bool
        """
        # Passability should be detected before collision. In general these two concepts are unrelated
        # but collision may change passability. In that case actor should enter the tile only on the next
        # turn, having wasted current one on cleaning the obstacle or killing enemy
        passability = self.map.entrance_possible(location)
        # Check if collision has occured
        collision_occured = False
        try:
            for item in self.map.get_column(location):
                # if type(item) is Actor:
                #     #  No need to collide with tiles or something
                if item.collide(self):
                    collision_occured = True
        except IndexError:
            #  Attempts to collide with something outside map boundaries are silently ignored
            pass
        moved = False
        if not collision_occured and passability:
            self.map.move_item(layer=self.layer,
                               old_location=self.location,
                               new_location=location)
            self.location = location
            self.map.game_events.append(GameEvent(event_type='moved',
                                                  actor=self))
            moved = True
            self.widget.last_move_animated = False
        return moved or collision_occured

    def pause(self):
        pass


class Trap(Construction):
    """
    A construction that acts if an Actor steps on it.
    Currently is a hardcoded landmine (deals 5 damage to everything on its tile and neighbours)
    """
    def __init__(self, **kwargs):
        super(Trap, self).__init__(**kwargs)
        self.primed = False

    def make_turn(self):
        if self.map.get_item(layer='actors', location=self.location) and self.primed:
            #  If there is an Actor on top of it
            self.map.game_events.append(GameEvent(event_type='exploded',
                                                  actor=self,
                                                  location=self.location))
            self.map.extend_log('A mine exploded')
            #  This event should be shot before any other events caused by explosion
            self.map.game_events.append(GameEvent(event_type='was_destroyed',
                                                  actor=self))
            #  Damage Actor on the same tile, if any
            victim = self.map.get_item(layer='actors',
                                       location=self.location)
            victim.fighter.get_damaged(5)
            #  Damage Actors and Constructions on neighbouring tiles
            for victim in self.map.get_neighbours(location=self.location,
                                                  layers=['actors', 'constructions']):
                if victim.fighter:
                    victim.fighter.get_damaged(5)
            self.map.delete_item(location=self.location,
                                 layer=self.layer)

        else:
            #  The landmine is primed when there is nobody on top of it.
            #  This is to prevent landmine exploding under the player right after he used it
            if not self.primed:
                self.primed = True