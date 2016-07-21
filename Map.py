#  Map and tile classes.
#  These contain only the information about things in game and some gameplay logic, so they don't inherit from
#  any of Kivy classes. MVC and all that.

from Actor import Actor
from Constructions import Construction
from math import sqrt
from GameEvent import GameEvent
from copy import deepcopy


class RLMap(object):
    def __init__(self, size=(10, 10), layers=['default']):
        self.size=size
        #  Initializing items container
        self.layers = layers
        self.items = {l: [[None for y in range(size[1])] for x in range(size[0])] for l in layers}
        #  Actors list
        self.actors = []
        self.constructions = []
        #  Log list. Initial values allow not to have empty log at the startup
        self.game_log = ['Игра начинается', 'Если вы видите этот текст, то кириллический лог работает',
                         'All the text below will be in English, so I guess Latin log works as well']
        #  GameEvent list
        self.game_events = []
        #  The Dijkstra map list, used for NPC pathfinding
        self.dijkstra = {x: {y: 1000 for y in range(self.size[1])} for x in range(self.size[0])}
        self.empty_dijkstra = deepcopy(self.dijkstra)

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
        self.items[layer][old_location[0]][old_location[1]] = None

    def get_item(self, layer='default', location=(0, 0)):
        """
        Return the map item on a given layer and location.
        :param layer:
        :param location:
        :return:
        """
        return self.items[layer][location[0]][location[1]]

    def get_column(self, location=(0, 0)):
        """
        Return a tuple of truthy objects in all layers at the given location
        :param location: int tuple
        :return:
        """
        return [self.items[layer][location[0]][location[1]] for layer in self.layers
                if self.items[layer][location[0]][location[1]]]

    def add_item(self, item=None, layer='default', location=(0, 0)):
        """
        Add the map item at the given layer and location.
        :param item:
        :param layer:
        :param location:
        :return:
        """
        self.items[layer][location[0]][location[1]] = item
        if isinstance(item, Actor) or isinstance(item, Construction):
            item.connect_to_map(map=self, location=location, layer=layer)
        if isinstance(item, Actor):
            self.actors.append(item)
        if isinstance(item, Construction):
            self.constructions.append(item)

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

    def delete_item(self, layer='default', location=(None, None)):
        """
        Delete the item at a given location, removing all references to it in the map object
        :param layer: str
        :param location: int tuple
        :return:
        """
        #  If the item deleted is an actor, it should be removed from self.actors as well as
        #  from self.items. Same 4 constructions
        if isinstance(self.items[layer][location[0]][location[1]], Actor):
            self.actors.remove(self.items[layer][location[0]][location[1]])
        if isinstance(self.items[layer][location[0]][location[1]], Construction):
            self.constructions.remove(self.items[layer][location[0]][location[1]])
        self.items[layer][location[0]][location[1]] = None
        #  If no other references exist (when this executes, one should probably be in GameEvent)
        #  Actor object will be garbage-collected. Please note that this method does not handle
        #  widget deletion. That one should be called according to GameEvent somehow
        #  Actor objects remain briefly within Controller method and are then kept in the inventory
        #  via Item.owner.actor

    #  Dijkstra map

    def _set_dijkstra_cell(self, location=(None, None), value=0):
        """
        Set Dijkstra value for a given cell.
        This method sets Dijksrta value for a cell and, if any of the neighbouring cells have Dijkstra
        value of more than value+1, calls itself on them recursively with value+1
        :param location:
        :param value:
        :return:
        """
        self.dijkstra[location[0]][location[1]] = value
        for n in self.get_neighbour_coordinates(location):
            if self.dijkstra[n[0]][n[1]] > value + 1:
                #  Check that there is neither impassable construction nor impassable bg item
                #  Cannot call self.entrance_possible here, as that would also check the actor, and
                #  cells under actors are subject to Dijkstra map calculations
                c = self.get_item(layer='constructions', location=n)
                bg = self.get_item(layer='bg', location=n)
                if bg.passable and (not c or c.passable):
                    self._set_dijkstra_cell(location=n, value=value+1)

    def update_dijkstra(self):
        """
        Update the Dijkstra map based on positions of PC and any PC-allied constructions.
        :return:
        """
        self.dijkstra = {k: {j:100 for j in range(self.size[1])} for k in range(self.size[0])}
        # self.dijkstra = deepcopy(self.empty_dijkstra)
        for actor in self.actors:
            if actor.faction.faction == 'pc':
                self._set_dijkstra_cell(location=actor.location, value=-5)
        for construction in self.constructions:
            if construction.faction and construction.faction.faction == 'pc':
                self._set_dijkstra_cell(location=construction.location, value=-2)
        # #  Place initial values under the player, player-allied constructions and impassable things.
        # #  This should be done every turn because player could potentially spawn constructions
        # #  and change passability
        # #  Set all passable tiles to 100
        # for x in range(self.size[0]):
        #     for y in range(self.size[1]):
        #         if self.entrance_possible(location=(x, y)):
        #            self.dijkstra[x][y] = 20
        #         else:
        #             self.dijkstra[x][y] = None
        # for construction in self.constructions:
        #     if construction.faction and construction.faction.faction == 'pc':
        #         self.dijkstra[construction.location[0]][construction.location[1]] = -2
        # #  Value actors above constructions. Also overwrite if player stands on allied construction
        # for actor in self.actors:
        #     if actor.faction.faction == 'pc':
        #         self.dijkstra[actor.location[0]][actor.location[1]] = -5
        #
        # #  Traverse the map a-la cellular automaton until equilibrium
        # has_changed = True
        # while has_changed:
        #     has_changed = False
        #     #  Have the copy so that traversal order doesn't affect results
        #     tmp = self.dijkstra[:][:]
        #     for x in range(self.size[0]):
        #         for y in range(self.size[1]):
        #             #  Don't waste time on impassable tiles
        #             if self.dijkstra[x][y]:
        #
        #                 neighbours = (self.dijkstra[j[0]][j[1]] for j in self.get_neighbour_coordinates(
        #                     location=(x, y)))
        #                 for n in neighbours:
        #                     if n and self.dijkstra[x][y] - n >= 2:
        #                         tmp[x][y] -= 1
        #                         has_changed = True
        #                         break
        #     self.dijkstra = tmp[:][:]


    #  Operations on neighbours

    def get_neighbour_coordinates(self, location=(None, None)):
        """
        Get the locations of all valid neighbour tiles.
        This method returns list of locations; for items, use get_neighbours()
        :param location: tuple of int
        :return:
        """
        ret = []
        for x in range(location[0]-1, location[0]+2):
            for y in range(location[1]-1, location[1]+2):
                try:
                    if x>0 and y>0:
                        self.get_item(location=(x,y), layer='bg')
                        ret.append((x, y))
                except IndexError:
                    pass
        return ret


    def get_neighbours(self, layers=['default'], location=(None, None)):
        """
        Get all the items in the cells connected to this one on given layers
        :param layers: list of layers of interest
        :param location: location
        :return:
        """
        l = []
        for layer in layers:
            l += [self.get_item(layer=layer, location=x)
                  for x in self.get_neighbour_coordinates(location=location)]
        # Filter out Nones and the item at (x, y)
        l = list(filter(lambda x: x is not None and not x.location == location, l))
        return l

    #  This isn't static method, because I intend to replace it by some proper distance calculation
    #  with pathfinding instead of a current euclidean placeholder sometime in the future
    def distance(self, location1=(None, None), location2=(None, None)):
        """
        Calculate distance between two locations
        :param location1:
        :param location2:
        :return:
        """
        return sqrt((location1[0]-location2[0])**2+(location1[1]-location2[1])**2)

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
                if tile is not None and not tile.passable:
                    #  Empty tiles are no problem: there may be a lot of those in eg actor layers
                    ret = False
                    break
            except IndexError:
                #  location beyond tile boundaries
                ret = False
                break
        return ret

    #  Displayable log

    def extend_log(self, item):
        """
        Add item to self.game_log
        Adds a string to the log (the one to be displayed on the screen) and emit a GameEvent
        so that a game widget will know to update it.
        :param item: string to be added
        :return:
        """
        assert isinstance(item, str)
        self.game_log.append(item)
        self.game_events.append(GameEvent(event_type='log_updated'))
