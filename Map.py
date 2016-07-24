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
        #  For some reason keeping tuple and creating list from it is way quicker than generating the list
        #  from scratch on every turn
        self.dijkstra = [[1000 for y in range(self.size[1])] for x in range(self.size[0])]
        self.empty_dijkstra = deepcopy(self.dijkstra)
        self.updated_now = set()
        self.max_distance = None

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
        Delete the item at a given location, making all necessary updates
        :param layer: str
        :param location: int tuple
        :return:
        """
        #  If the item deleted is an actor, it should be removed from self.actors as well as
        #  from self.items. Same 4 constructions.
        #  Removing items of PC faction also requires editing Dijkstra maps to decrease attractiveness of
        #  its former position.
        item = self.items[layer][location[0]][location[1]]
        if isinstance(item, Actor):
            self.actors.remove(item)
        if isinstance(item, Construction):
            self.constructions.remove(item)
        self.items[layer][location[0]][location[1]] = None
        #  If no other references exist (when this executes, one should probably be in GameEvent)
        #  Actor object will be garbage-collected. Please note that this method does not handle
        #  widget deletion. That one should be called according to GameEvent somehow
        #  Actor objects remain briefly within Controller method and are then kept in the inventory
        #  via Item.owner.actor

    #  Dijkstra map

    ####
    # This implementation of Dijkstra map filling algorithm is commented out as it is extremely slow.
    # However, it surely does work with multiple attractors, which are yet to be implemented in _breadth_fill()
    #######

    # def _set_dijkstra_cell(self, location=(None, None), value=0, spread_direction = 'down', callers=set()):
    #     """
    #     Set Dijkstra value for a given cell.
    #     This method sets Dijksrta value for a cell and tries to spread it to any neighbouring cells/
    #     Depending on 'spread_direction' attribute it will attempt to either lower it (default)
    #     or raise. Lowering is intended to be done after addition of attractive item (ie PC entering tile
    #     starts attracting enemies) while raising is intended for a removal of such item (ie PC *leaving*
    #     tile or construction being destroyed stops being of any interest).
    #     Although recursively increasing Dijkstra values is supposed to be a quick-and-dirty cleanup after player
    #     has moved away, it still needs to cover most, if not all, the map
    #     :param value: int. A value the cell gets
    #     :param spread_direction: str, one of 'up' or 'down'
    #     :return:
    #     """
    #     self.dijkstra[location[0]][location[1]] = value
    #     self.updated_now.add(tuple(location))
    #     if spread_direction == 'down':
    #         for n in self.get_neighbour_coordinates(location):
    #             if tuple(n) not in self.updated_now or self.dijkstra[n[0]][n[1]] > value + 1:
    #                 #  Check that there is neither impassable construction nor impassable bg item
    #                 #  Cannot call self.entrance_possible here, as that would also check the actor, and
    #                 #  cells under actors are subject to Dijkstra map calculations
    #                 c = self.get_item(layer='constructions', location=n)
    #                 bg = self.get_item(layer='bg', location=n)
    #                 if bg.passable and (not c or c.passable):
    #                     self._set_dijkstra_cell(location=n, value=value+1)
    #     elif spread_direction == 'up':
    #         for n in self.get_neighbour_coordinates(location):
    #             if self.dijkstra[n[0]][n[1]] < value - 1:
    #                 c = self.get_item(layer='constructions', location=n)
    #                 bg = self.get_item(layer='bg', location=n)
    #                 if bg.passable and (not c or c.passable):
    #                     self._set_dijkstra_cell(location=n, value=value-1, spread_direction='up')
    #     else:
    #         raise ValueError('spread_direction should be either\'up\' or \'down\'')

    def _breadth_fill(self, filled=set(), value=-5):
        """
        Fill Dijkstra map breadth-first.
        This method is recursive and is intended to be started from a single point. Multiple attractors are
        currently not supported (although multiple starting points *may* work if they all have exactly the same
        value. This method relies on at least one cell of Dijkstra map being filled with value and placed
        in self.updated_now by the moment it's (non-recursively) called.
        :param filled: set. Set of cells (as coordinate tuples) filled on a previous iteration
        :param value: int. Value that the cells from a `filled` set contain
        :return:
        """
        s = set()
        for cell in filled:
            for n in self.get_neighbour_coordinates(cell):
                bg = self.get_item(layer='bg', location=n)
                c = self.get_item(layer='constructions', location=n)
                #  Ignore impassable cells and cells with impassable factionless constructions
                if n not in self.updated_now and bg.passable and (not c or c.passable or c.faction):
                    s.add(n)
        if s:
            for cell in s:
                self.dijkstra[cell[0]][cell[1]] = value + 1
            self.updated_now = self.updated_now.union(s)
            self._breadth_fill(filled=s, value=value+1)
        else:
            return

    def update_dijkstra(self):
        """
        Update the Dijkstra map based on positions of PC and any PC-allied constructions.
        :return:
        """
        # self.dijkstra = list(self.empty_dijkstra)
        self.updated_now = set()
        actor = self.actors[0]
        self.dijkstra[actor.location[0]][actor.location[1]] = -5
        self.updated_now.add(tuple(actor.location))
        self._breadth_fill(value=-5, filled=set((tuple(actor.location),)))

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
                    if x >= 0 and y >= 0 and not (x, y) == location:
                        #  This line will raise IndexError if it's outside map boundaries
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
