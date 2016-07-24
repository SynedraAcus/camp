"""
Actor classes. Also contains other classes (components, TurnReport) that are necessary for actors'
functioning, but are not, strictly speaking, related to graphics
"""

from Controller import Controller, PlayerController, AIController
from MapItem import MapItem
from GameEvent import GameEvent





class Actor(MapItem):
    def __init__(self,
                 image_source='NPC.png',
                 controller=None, fighter=None, descriptor=None,
                 inventory=None, faction=None,
                 **kwargs):
        #  Actors should be impassable by default. The 'passable' should be in kwargs to be passed to
        #  superclass constructor, so a simple default value in signature won't work here
        if 'passable' not in kwargs.keys():
            kwargs.update({'passable': False})
        super(Actor, self).__init__(**kwargs)
        self.attach_controller(controller)
        self.fighter = fighter
        if descriptor:
            self.descriptor = descriptor
        self.inventory = inventory
        for a in (self.fighter, self.inventory, self.controller, self.descriptor):
            if a:
                a.actor = self
        #  Faction component
        self.faction = faction
        self.image_source = image_source
        #  These attributes are not set by constructor: it is only defined when map factory
        # places the actor on the map
        self.widget = None
        self.map = None
        self.location = None

    def connect_to_map(self, map=None, layer=None, location=(None, None)):
        """
        Remember that this actor was placed to a given map and a given location
        :param map: RLMap
        :param location: tuple
        :return:
        """
        self.map = map
        self.layer = layer
        #  Cast the type: location attribute was possibly a tuple
        self.location = list(location)
        #  Effects of Items in actor's can possibly need to know about the map as well
        #  Items themselves don't need it because they can look in self.owner.actor.map
        if self.inventory and len(self.inventory)>0:
            for i in self.inventory:
                if hasattr(i.effect, 'map'):
                    i.effect.map = map

    def attach_controller(self, controller):
        """
        Attach a controller to the Actor
        :param controller: Controller
        :return:
        """
        assert isinstance(controller, Controller)
        self.controller = controller
        self.controller.actor = self


    def make_turn(self):
        """
        Make turn: move, attack or something. Asks a controller to actually do stuff, but
        handles other turn-related stuff.
        Returns True if this actor has managed to do something
        :return: bool
        """
        #  Prevent dead actors from making turns. If I'm correct, they act just because GC doesn't get to them
        #  quickly enough to prevent that. If, on the other hand, I've missed an Actor reference somewhere,
        #  this is a potential memory leak.
        if self.fighter and self.fighter.hp <= 0:
            return False
        if not isinstance(self.controller, PlayerController):
            self.controller.choose_actor_action()
        r = self.controller.call_actor_method()
        if isinstance(self.controller, PlayerController):
            #  This should be done *after* player move!
            self.map.update_dijkstra()
        return r

    #  These methods are expected to be called by Controller. They all return True if action could be performed
    #  (not necessarily successfully!!!), False otherwise

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
                    break
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
        """
        Spend one turn doing nothing. Return True if it was possible, False otherwise
        :return:
        """
        return True

    def grab(self):
        """
        Spend one turn to grab item from the ground, if there is one, and report to game_events
        and game_log
        Return True if there was an item to grab, False otherwise
        :return:
        """
        i = self.map.get_item(location=self.location, layer='items')
        if i:
            if len(self.inventory) < self.inventory.volume:
                self.inventory.append(i)
                self.map.delete_item(location=self.location, layer='items')
                self.map.game_events.append(GameEvent(event_type='picked_up', actor=self,
                                                      location=self.location))
                self.map.extend_log('{0} picked up {1}'.format(self.descriptor.name,
                                                               i.name))
                return True
            else:
                self.map.extend_log('Inventory is full already!')
                return False
        else:
            return False

    def use_item(self, item_number):
        """
        Spend one turn to use item from inventory.
        Return True if use was successful, False otherwise
        :param item_number: int
        :return:
        """
        try:
            return self.inventory[item_number].use()
        except IndexError:
            return False

    def drop_item(self, item_number):
        """
        Spend one turn to drop item from inventory
        Item can only be dropped to a tile where there isn't item already.
        :param item_number:
        :return:
        """
        if not self.map.get_item(location=self.location, layer='items'):
            try:
                self.map.add_item(item=self.inventory[item_number], location=self.location, layer='items')
                self.map.extend_log('{0} dropped {1}'.format(self.descriptor.name,
                                                             self.inventory[item_number].name))
                self.inventory.remove(self.inventory[item_number])
                self.map.game_events.append(GameEvent(event_type='dropped', actor=self,
                                                      location=self.location))
                return True
            except IndexError:
                #  No attempts to drop non-existent items!
                return False
        else:
            return False

    def collide(self, other):
        """ Collision callback: get bumped into by some other actor.
        :param other: Actor
        :return:
        """
        if self.fighter and other.fighter:
            self.map.game_events.append(GameEvent(event_type='attacked',
                                                  actor=other, location=self.location))
            self.fighter.get_damaged(other.fighter.attack())
            #  Collision did happen and take colliding actor's turn, whether it damaged target or not
            return True
