#  Map and tile classes.
#  These contain only the information about things in game and some gameplay logic, so they don't inherit from
#  any of Kivy classes. MVC and all that.

from copy import deepcopy

from Actor import Actor
from Constructions import Construction
from Controller import PlayerController
from GameEvent import GameEvent


class RLMap(object):
    def __init__(self, size=(10, 10), layers=['default']):
        self.size=size
        #  Initializing items container
        self.layers = layers
        self.items = {l: [[None for y in range(size[1])] for x in range(size[0])] for l in layers}
        #  Actors list
        self.actors = []
        self.constructions = []
        #  GameEvent queue and GameManager object
        self.game_events = None
        self.game_manager = None
        #  The Dijkstra map list and related variables
        self.dijkstra = [[1000 for y in range(self.size[1])] for x in range(self.size[0])]
        self.empty_dijkstra = deepcopy(self.dijkstra)
        self.updated_now = set()
        #  Neighbouring maps
        self.neighbour_maps = {}

    def register_manager(self, game_manager):
        """
        Register a queue to which this Map will add its GameEvents
        :return:
        """
        self.game_manager = game_manager
        self.game_events = game_manager.queue

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
        Return a list of truthy objects in all layers at the given location
        :param location: int tuple
        :return:
        """
        return [self.items[layer][location[0]][location[1]] for layer in self.layers
                if self.items[layer][location[0]][location[1]]]

    def get_top_item(self, location=(0, 0)):
        """
        Return the topmost item in a given column
        :param location:
        :return:
        """
        return self.get_column(location=location)[-1]

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
            if isinstance(item.controller, PlayerController):
                self.actors.insert(0, item)
            else:
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
                if n not in self.updated_now:
                    if bg.passable and (not c or c.passable or c.faction):
                        s.add(n)
                    else:
                        self.dijkstra[n[0]][n[1]] = 1000
                        self.updated_now.add(n)
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

    #  Complex operations on map

    def get_neighbour_coordinates(self, location=(None, None), return_query=False):
        """
        Get the locations of all valid neighbour tiles.
        This method returns list of locations; for items, use get_neighbours().
        :param location: tuple of int
        :param return_query: bool. Whether to include the location from argument to return list
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
        if return_query:
            ret.append(location)
        return ret

    def get_neighbours(self, layers=['default'], location=(None, None), return_query=False):
        """
        Get all the items in the cells connected to this one on given layers
        :param layers: list of layers of interest
        :param location: location
        :param return_query: bool. Whether to include items in the tile from argument
        :return:
        """
        l = []
        for layer in layers:
            l += [self.get_item(layer=layer, location=x)
                  for x in self.get_neighbour_coordinates(location=location, return_query=return_query)]
        # Filter out Nones and the item at (x, y)
        l = list(filter(lambda x: x is not None and not (x.location == location and not return_query), l))
        return l

    def get_shootable_in_range(self, location=(None, None), layers=['default'], distance=1,
                               exlcude_neighbours=False):
        """
        Get all the map items in the given layers that are no more than `range` steps away from `location` and can be shot.
        This method is relatively slow as it performs air-entrance Bresenham check; for quicker lookup
        other methods, such as `get_neighbours`, should be used. This method is linear from number of items found,
        thus approx. O^2 from distance. Thus, it may cause lag for extremely large ranges
        :param location: int tuple. location of shooter
        :param distance: int. range of target search
        :param layers: str list/tuple. Layers at which targets will be looked for
        :param exlcude_neighbours: bool. If True, items at distance of 1 are not returned
        :return:
        """
        #  This hack works solely because the cost of diagonal movement is the same as for cardinal direction, and,
        #  therefore, a set of tiles with the same distance to target tile forms square. With more realistic
        #  diagonal movement cost of sqrt(2) this set would've formed something circle-ish and the proper breadth
        #  search would've been necessary
        neighbours = set()
        #  Border check. Will fail with negative distance, but that makes no sense anyway.
        xrange = [location[0]-distance, location[0]+distance+1]
        if xrange[0] < 0:
            xrange[0] = 0
        if xrange[1] > self.size[0]:
            xrange[1] = self.size[0]
        yrange = [location[1]-distance, location[1]+distance+1]
        if yrange[0] < 0:
            yrange[0] = 0
        if yrange[1] > self.size[1]:
            yrange[1] = self.size[1]
        for x in range(xrange[0], xrange[1]):
            for y in range(location[1]-distance, location[1]+distance+1):
                for l in layers:
                    i = self.get_item(location=(x, y), layer=l)
                    if i:
                        neighbours.add(i)
        #  Select air-reachable items. Relies on item having `location` attribute and thus makes sense
        #  only for Actors and Constructions (as of now)
        r = []
        for item in neighbours:
            line = self.get_line(location, item.location)
            if line[-1] == item.location and (len(line) > 2 or not exlcude_neighbours):
                r.append(item)
        return r


    def get_line(self, start=(None, None), end=(None, None)):
        """
        Return the path from starting point to endpoint as a list of coordinates.
        This method uses Bresenham line-drawing algorithm and stops iteration on reaching the tile,
        that isn't air-passable, even if it hasn't reached end. The entire method, save for impassability check
        and `if start==end` sanity check,is copied from Roguebasin:
        http://www.roguebasin.com/index.php?title=Bresenham%27s_Line_Algorithm#Python
        :param start:
        :param end:
        :return:
        """
        #  Just in case, for example self-targeting with rockets
        #  `start == end` doesn't work for some reason
        if start[0] == end[0] and start[1] == end[1]:
            return [start]
        x1, y1 = start
        x2, y2 = end
        dx = x2 - x1
        dy = y2 - y1
        is_steep = abs(dy) > abs(dx)
        if is_steep:
            x1, y1 = y1, x1
            x2, y2 = y2, x2
        swapped = False
        if x1 > x2:
            x1, x2 = x2, x1
            y1, y2 = y2, y1
            swapped = True
        dx = x2 - x1
        dy = y2 - y1
        error = int(dx/2.0)
        ystep = 1 if y1 < y2 else -1
        #  Iteration
        y = y1
        points = []
        for x in range(x1, x2+1):
            coord = (y, x) if is_steep else (x, y)
            points.append(coord)
            error -= abs(dy)
            if error < 0:
                y += ystep
                error += dx
        if swapped:
            points.reverse()
        #  Shorten points until the first air-impassable tile, not including the very start
        for a in range(1, len(points)):
            if not self.air_entrance_possible(points[a]):
                break
        return points[:a+1]

    def air_entrance_possible(self, location):
        """
        Return True if given coordinates correspond to a valid fly destinaton (ie air_passable tile within
        map borders)
        :param location:
        :return:
        """
        ret = True
        for layer in self.items.keys():
            try:
                tile = self.get_item(layer=layer, location=location)
                if tile is not None and not tile.air_passable:
                    #  Empty tiles are no problem: there may be a lot of those in eg actor layers
                    ret = False
                    break
            except IndexError:
                #  location beyond tile boundaries
                ret = False
                break
        return ret

    def entrance_possible(self, location):
        """
        Return true, if given coordinates correspond to a valid move destination (ie passable tile
        within map borders)
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
        self.game_manager.game_log.append(item)
        self.game_events.append(GameEvent(event_type='log_updated'))

    def process_turn(self, command=None):
        """
        Make one turn, passing command to PC.
        This method passes the command to self.actors[0].controller, asks the same to make a turn and, if
        successful, does the same for all the actors and constructions (in that order). Then it calls for animation
        to be drawn, even if PC turn wasn't actually possible. That's because calling for impossible turn could've
        potentially updated game log or caused other visible effects.
        :return:
        """
        self.actors[0].controller.accept_command(command)
        r = self.actors[0].make_turn()
        if r:
            for a in self.actors[1:]:
                a.make_turn()
            for a in self.constructions:
                a.make_turn()
        self.game_events.pass_all_events()
