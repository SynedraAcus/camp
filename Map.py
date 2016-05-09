#  Map and tile classes.
#  These contain only the information about things in game and some gameplay logic, so they don't inherit from
#  any of Kivy classes. MVC and all that.

from copy import copy
import Controller

class MapItem(object):
    """
    Base class from which all items that can be placed on map should inherit
    """
    def __init__(self, passable=True):
        self.passable=passable

    def collide(self, other):
        """ Collisions are expected to be overloaded if they are to actually do something.
        This method returns False indicating that nothing actually happened."""
        return False

class GroundTile(MapItem):
    def __init__(self, passable=True, image_source='Tmp_frame.png', **kwargs):
        super(GroundTile, self).__init__(**kwargs)
        self.passable=passable
        self.image_source = image_source
        #  Widget should be defined when a tile is added to the RLMapWidget using TileWidgetFactory
        self.widget = None

class Actor(MapItem):
    def __init__(self, player=False, name='Unnamed actor', **kwargs):
        #  Actors should be impassable by default
        if 'passable' not in kwargs.keys():
            kwargs.update({'passable': False})
        super(Actor, self).__init__(**kwargs)
        #  Set to true if this is a player-controlled actor
        self.player=player
        if self.player:
            #  Attach controller to a PC
            self.attach_controller(Controller.create_prototype_controller())
        self.name = name
        #  Here will be data re: map location (in tiles, not pixels)
        #  This is not set by constructor: it is only defined when map factory places the actor on the map
        self.map = None
        self.location=[]

    def connect_to_map(self, map=None, layer=None, location=(None, None)):
        """
        Remember that this actor was placed to a given map and a given location
        :param map: RLMap
        :param location: tuple
        :return:
        """
        self.map = map
        self.layer = layer
        #  Cast the type: location attribute was a tuple
        self.location = list(location)

    def attach_controller(self, controller):
        """
        Attach a controller to the Actor
        :param controller: Controller
        :return:
        """
        assert type(controller) is Controller.Controller
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
        Make turn: move, attack or something. If an actor has player=True, it respects self.last_command.
        Otherwise this method makes the decision and calls the appropriate method to perform it.
        Returns True if this actor has managed to do something
        :return: bool
        """
        if self.player:
            return self.controller.call_actor_method()
        else:
            return self.move(location=(self.location[0]+1, self.location[1]+1))

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
        # turn, having vasted current one on cleaning the obstacle or killing enemy
        passability = self.map.entrance_possible(location)
        # Check if collision has occured
        collision_occured = False
        try:
            for item in self.map.get_column(location):
                if type(item) is Actor:
                    #  No need to collide with tiles or something
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
            moved = True
            self.widget.last_move_animated = False
        return moved or collision_occured

    def pause(self):
        """
        Spend one turn doing nothing. Return True if it was possible, False otherwise
        :return:
        """
        return True

    def collide(self, other):
        """ Collision callback: get bumped into by some other actor.
        :param other: Actor
        :return:
        """
        if self.map.entrance_possible((1, 1)):
            self.map.game_log.append('{0} successfully teleported by {1}'.format(self.name,
                                                                                   other.name))
            return self.move(location=(1, 1))
        else:
            #  Collision did happen, but teleportation turned out to be broken
            self.map.game_log.append('{1} attempted to teleport {0}, but failed'.format(self.name,
                                                                                          other.name))
            return True
        # return True



class RLMap(object):
    def __init__(self, size=(10, 10), layers = ['default']):
        self.size=size
        #  Initializing items container
        self.items ={l: [[None for x in range(size[1])] for y in range(size[0])] for l in layers}
        #  Actors list
        self.actors = []
        #  Log list. Initial values allow not to have empty log at the startup
        self.game_log = ['Игра начинается', 'Если вы видите этот текст, то лог работает',
                         'All the text below will be in English']

    #  Actions on map items: addition, removal and so on

    def move_item(self, layer='default', old_location=(0, 0), new_location=(1, 1)):
        """
        Move the map item to a new location. Place None in its old position. Does not move items between layers
        :param layer: Layer in which the moved object is (str)
        :param old_location: Where to take item from (2-int tuple)
        :param new_location: Where to place the item (2-int tuple)
        :return:
        """
        moved_item=self.get_item(layer=layer, location=old_location)
        self.items[layer][new_location[0]][new_location[1]] = moved_item
        self.delete_item(layer=layer, location=old_location)

    def get_item(self, layer='default', location=(0, 0)):
        """
        Return the map item on a given layer and location.
        :param layer:
        :param location:
        :return:
        """
        return self.items[layer][location[0]][location[1]]

    def get_column(self, location=(0,0)):
        """
        Return a tuple of truthy objects in all layers in the given location
        :param location: int tuple
        :return:
        """
        return (self.items[layer][location[0]][location[1]] for layer in self.items.keys()
                if self.items[layer][location[0]][location[1]])

    def add_item(self, item=None, layer='default', location=(0, 0)):
        """
        Add the map item at the given layer and location.
        :param item:
        :param layer:
        :param location:
        :return:
        """
        self.items[layer][location[0]][location[1]] = item
        if type(item) is Actor:
            self.actors.append(item)
            item.connect_to_map(map=self, location=location, layer=layer)

    def has_item(self, layer='default', location=(None, None)):
        """
        Return True if there is anything at the given layer and location.
        :param layer:
        :param location:
        :return:
        """
        if self.items[layer][location[0]][location[1]] is not None:
            return True
        else:
            return False

    def delete_item(self, layer='default', location=(None,None)):
        """
        Remove whatever is at the given layer and location.
        :param layer:
        :param location:
        :return:
        """
        self.items[layer][location[0]][location[1]] = None

    #  Game-related actions

    def process_turn(self, keycode):
        """
        Perform a turn. This procedure is called when player character makes a turn; later I might
        implement a more complex time system.
        :param keycode: kivy keycode tuple
        :return:
        """
        for actor in self.actors:
            if actor.player:
                actor.pass_command(keycode)
            actor.make_turn()

    def entrance_possible(self, location):
        """
        Return true, if a given coordinates correspond to a valid move destination (ie passable tile
        within borders of the map)
        :param location: tuple
        :return: bool
        """
        ret = True
        for layer in self.items.keys():
            try:
                tile = self.get_item(layer=layer, location=location)
                if tile is not None and tile.passable == False:
                    #  Empty tiles are no problem: there may be a lot of those in eg actor layers
                    ret = False
                    break
            except IndexError:
                #  location beyond tile boundaries
                ret = False
                break
        return ret
