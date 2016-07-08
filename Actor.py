"""
Actor classes. Also contains other classes (components, TurnReport) that are necessary for actors'
functioning, but are not, strictly speaking, related to graphics
"""

from Controller import Controller, PlayerController, AIController
from MapItem import MapItem
from GameEvent import GameEvent





class Actor(MapItem):
    def __init__(self, player=False,
                 image_source='NPC.png',
                 controller=None, fighter=None, descriptor=None,
                 inventory=None, faction=None,
                 **kwargs):
        #  Actors should be impassable by default. The 'passable' should be in kwargs to be passed to
        #  superclass constructor, so a simple default value in signature won't work here
        if 'passable' not in kwargs.keys():
            kwargs.update({'passable': False})
        super(Actor, self).__init__(**kwargs)
        #  Set to true if this is a player-controlled actor
        self.player = player
        self.attach_controller(controller)
        #  Combat component
        self.fighter = fighter
        if self.fighter: #  Might be None
            self.fighter.actor = self
        #  Description component
        if descriptor:
            self.descriptor = descriptor
            self.descriptor.actor = self
        # else:
        #     self.descriptor = DescriptorComponent()
        #  Inventory component
        if inventory:
            self.inventory = inventory
            self.inventory.actor = self
        #  Faction component
        self.faction = faction
        #  These attributes are not set by constructor: it is only defined when map factory
        # places the actor on the map
        self.image_source = image_source
        self.widget = None
        self.map = None
        self.location = []

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

    def attach_controller(self, controller):
        """
        Attach a controller to the Actor
        :param controller: Controller
        :return:
        """
        assert isinstance(controller, Controller)
        self.controller = controller
        self.controller.actor = self

    def pass_command(self, keycode):
        """
        Pass the last key that was pressed. This method is intended to be called before make_turn() for
        a player-controlled Actor, so that the Actor will do whatever player wants instead of making its
        own decisions.
        :param keycode: kivy keycode tuple
        :return:
        """
        try:
            self.controller.take_keycode(keycode)
        except AttributeError:
            raise NotImplementedError('Commands to non-player Actors are not implemented')

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
        return self.controller.call_actor_method()

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
        except IndexError:
            #  Attempts to collide with something outside map boundaries are silently ignored
            pass
        moved = False
        if passability:
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
            self.inventory.append(i)
            self.map.delete_item(location=self.location, layer='items')
            self.map.game_events.append(GameEvent(event_type='picked_up', actor=self,
                                                  location=self.location))
            self.map.extend_log('{0} picked up {1}'.format(self.descriptor.name,
                                                           i.name))
            return True
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
            a = other.fighter.attack()
            d = self.fighter.defense()
            self.map.game_events.append(GameEvent(event_type='attacked',
                                                  actor=other, location=self.location))
            if a > d:
                self.fighter.hp -= a-d
                self.map.extend_log('{1} hit {0} for {2} damage ({3}/{4})'.format(self.descriptor.name,
                                                                                  other.descriptor.name,
                                                                                  a-d, a, d))
            else:
                self.map.extend_log('{1} missed {0}({3}/{4})'.format(self.descriptor.name,
                                                                     other.descriptor.name,
                                                                     a, d))
            if self.fighter.hp <= 0:
                #  Death
                self.map.extend_log('{} was killed'.format(self.descriptor.name))
                self.map.game_events.append(GameEvent(event_type='was_destroyed',
                                                      actor=self))
                if self.inventory and len(self.inventory) > 0:
                    #  Drop the first inventory item if the tile is empty
                    if not self.map.get_item(layer='items', location=self.location):
                        self.drop_item(0)
                self.map.delete_item(layer='actors', location=self.location)
                #  By this moment GameEvent should be the only thing holding the actor reference.
                #  When it is animated and then removed, Actor instance will be forgotten
            return True
