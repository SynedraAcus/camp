#  Map and tile classes.
#  These contain only the information about things in game and some gameplay logic, so they don't inherit from
#  any of Kivy classes. MVC and all that.

from copy import copy
# import Controller
from Actor import Actor


class RLMap(object):
    def __init__(self, size=(10, 10), layers = ['default']):
        self.size=size
        #  Initializing items container
        self.items = {l: [[None for x in range(size[1])] for y in range(size[0])] for l in layers}
        #  Actors list
        self.actors = []
        #  Log list. Initial values allow not to have empty log at the startup
        self.game_log = ['Игра начинается', 'Если вы видите этот текст, то кириллический лог работает',
                         'All the text below will be in English, so I guess Latin log works as well']

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
        self.empty_map_tile(layer=layer, location=old_location)

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

    def empty_map_tile(self, layer='default', location=(None, None)):
        """
        Remove whatever is at the given layer and location. Do not actually
        try to remove all references to the object in question, just empty tile
        :param layer:
        :param location:
        :return:
        """
        self.items[layer][location[0]][location[1]] = None

    def delete_item(self, layer='default', location=(None, None)):
        """
        Delete the item at a given location, removing all references to it that map knows about
        :param layer: str
        :param location: int tuple
        :return:
        """
        #  We need to remove widget as well as the map reference
        w = self.items[layer][location[0]][location[1]].widget
        w.parent.remove_widget(w)
        self.items[layer][location[0]][location[1]] = None
        #  If the item deleted is an actor, it should be removed from self.actors as well as
        #  from self.items
        if isinstance(self.items[layer][location[0]][location[1]], Actor):
            self.actors.remove(self.items[layer][location[0]][location[1]])

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
