"""
Game map and its pathfinding representation.
"""

from Actor import Actor
from Constructions import Construction, Upgrader
from Controller import PlayerController
from GameEvent import GameEvent
from Listeners import Listener


class DijkstraMap(Listener):
    """
    A container for Dijkstra map data.
    Any particular instance of this map listens to events so that it could update.
    """
    def __init__(self, map=None, event_filters={}, attractor_filters=[]):
        """
        Constructor
        :param map: RLMap instance
        :param event_filters: dict of {event_type: lambda event: event_is_attractor(event)}. If True, DijkstraMap
        will set event's actor as an attractor (if it's not one already) and trigger map rebuilding. If event is
        of `was_destroyed` type, actor is instead removed from attractors and map is rebuilt.
        :param attractor_filters: list of functions that accept MapItem and return True if it's an attractor
        :return:
        """
        self._values = []
        if not map:
            raise ValueError('DijkstraMap requires map to be created')
        self.map = map
        self.updated_now = set()
        if len(event_filters.keys()) == 0:
            raise ValueError('DijkstraMap cannot be created with empty event filter')
        self.event_filters = event_filters
        #  There can be no attractor_filters if whatever this map is about doesn't get created before
        #  the game starts.
        self.attractor_filters = attractor_filters
        self.attractors = []

    def rebuild_self(self):
        """
        Build a fresh Dijkstra map for a newly-attached map
        :return:
        """
        #  Initializing data container. It should be the same size as the map in question
        self._values = [[None for x in range(self.map.size[1])] for y in range(self.map.size[0])]
        for x in range(self.map.size[0]):
            for y in range(self.map.size[1]):
                if self.should_ignore((x, y)):
                    self.set_value(location=(x, y), value=None)
                else:
                    #  Way above anything possible on a reasonable-sized map of a reasonable topology, but
                    #  can be easily raised to 10k or something for obscure cases.
                    self.set_value(location=(x, y), value=1000)
        #  Now that initial values are placed, initial attractors (if any) are used to place initial values
        if not self.attractors:
            if len(self.attractor_filters) > 0:
                for x in range(self.map.size[0]):
                    for y in range(self.map.size[1]):
                        for item in self.map.get_column(location=(x, y)):
                            for attractor_function in self.attractor_filters:
                                if attractor_function(item):
                                    self.attractors.append(item)
        #  There is no reason to call self.update() if there are still zero attractors
        if self.attractors:
            self.update()

    def should_ignore(self, location):
        """
        Return True if this map location should be ignored during DijkstraMap upgrade.
        Currently tiles with impassable BG and impassable factionless constructs are ignored
        :param column:
        :return:
        """
        bg = self.map.get_item(location=location, layer='bg')
        c = self.map.get_item(location=location, layer='constructions')
        if not bg or not bg.passable:
            return True
        if c and (not c.passable and (not c.faction or c.faction not in ('pc', 'npc'))):
            return True
        return False

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
            for n in self.map.get_neighbour_coordinates(cell):
                if n not in self.updated_now:
                    if not self.should_ignore(n):
                        s.add(n)
                    else:
                        self.set_value(location=(n[0], n[1]), value=None)
                        self.updated_now.add(n)
        if s:
            for cell in s:
                if self[cell[0]][cell[1]] >= value+1:
                    self.set_value(location=cell, value=value + 1)
            self.updated_now = self.updated_now.union(s)
            self._breadth_fill(filled=s, value=value+1)
        else:
            return

    def update(self, location=(None, None), value=None):
        """
        Set a single cell to a given value and update everything it can change
        :param location:
        :param value:
        :return:
        """
        for x in range(len(self)):
            for y in range(len(self[0])):
                if self.should_ignore((x, y)):
                    self.set_value(location=(x, y), value=None)
                else:
                    self.set_value(location=(x, y), value=1000)
        filled = set()
        for attractor in self.attractors:
            self.updated_now = set()
            self.updated_now.add(tuple(attractor.location))
            filled.add(tuple(attractor.location))
            self.set_value(location=attractor.location, value=0)
        self._breadth_fill(value=0, filled=filled)

    def set_value(self, location=(None, None), value=None):
        """
        Set value of a single cell.
        This method shouldn't be used outside the class, because it doesn't trigger recursive update of a map.
        For that, use `self.update()`
        :param location:
        :param value:
        :return:
        """
        self._values[location[0]][location[1]] = value

    def process_game_event(self, event):
        """
        Processes the event if it is interesting (as determined by self.event_filters)
        Adds or removes event.actor to self.attractors, if necessary, and triggers self.update()
        :param event:
        :return:
        """
        if event.event_type in self.event_filters.keys():
            if self.event_filters[event.event_type](event):
                if event.actor not in self.attractors:
                    self.attractors.append(event.actor)
                elif event.event_type == 'was_destroyed':
                    self.attractors.remove(event.actor)
                self.update()

    def __getitem__(self, item):
        """
        Allows DijkstraMap()[x][y]. DijkstraMap()[x, y] is not supported.
        Neither is __setitem__, because it creates unnecessary problems with nested lists
        :param item:
        :return:
        """
        #  This class is two-dimensional and is expected to be called like this: `map_object[x][y]`
        #  Therefore, call to __getitem__ returns a whole row and getting to element within it is a row's
        #  business.
        return self._values[item]

    def __len__(self):
        return len(self._values)


class RLMap(object):
    def __init__(self, size=(10, 10), layers=['default']):
        self.size = size
        #  Initializing items container
        self.layers = layers
        self.items = {l: [[None for y in range(size[1])] for x in range(size[0])] for l in layers}
        #  Actors list
        self.actors = []
        self.constructions = []
        #  GameEvent queue and GameManager object
        self.game_events = None
        self.game_manager = None
        #  The Dijkstra maps
        #  Somehow it feels like it doesn't belong here, but I'm not sure where it should be
        self.dijkstras = {
                        #  A map that has PC as the sole attractor. Used by all AI for combat
                        'PC': DijkstraMap(map=self,
                                            event_filters={'moved':
                                              lambda x: isinstance(x.actor, Actor)
                                                  and isinstance(x.actor.controller, PlayerController),
                                                           'was_destroyed':
                                              lambda x: isinstance(x.actor, Actor)
                                                  and isinstance(x.actor.controller, PlayerController)},
                                            attractor_filters=[
                                              lambda x: isinstance(x, Actor)
                                                  and isinstance(x.controller, PlayerController)
                                            ]),
                        #  A map that uses all upgraders as attractors. Doesn't (yet) check factions
                        'upgraders': DijkstraMap(map=self, event_filters={
                            'construction_spawned': lambda x: isinstance(x.actor, Upgrader),
                            'was_destroyed': lambda x: isinstance(x.actor, Upgrader)},
                                                attractor_filters=[
                                                    lambda x: isinstance(x, Upgrader)
                                                ]
                                                )}
        #  Neighbouring maps
        self.neighbour_maps = {}
        self.entrance_message = ''

    def register_manager(self, game_manager):
        """
        Register a queue to which this Map will add its GameEvents
        :return:
        """
        self.game_manager = game_manager
        self.game_events = game_manager.queue
        for dijkstra in self.dijkstras.values():
            self.game_events.register_listener(dijkstra)

    def rebuild_dijkstras(self):
        """
        This method should be called after MapFactory has finished building this map
        :return:
        """
        for x in self.dijkstras.values():
            x.rebuild_self()

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
        neighbours = {}
        #  Border check. Will fail with negative distance, but that makes no sense anyway.
        xrange = [location[0]-distance, location[0]+distance+1]
        if xrange[0] < 0:
            xrange[0] = 0
        if xrange[1] > self.size[0]:
            xrange[1] = self.size[0]
        yrange = [location[1]-distance, location[1]+distance+1]
        if yrange[0] < 0:
            yrange[0] = 0
        if yrange[1] > self.size[1]-1:
            yrange[1] = self.size[1]-1
        for x in range(xrange[0], xrange[1]):
            for y in range(yrange[0], yrange[1]):
                for l in layers:
                    i = self.get_item(location=(x, y), layer=l)
                    if i:
                        neighbours[i] = None
        #  Select air-reachable items. Relies on item having `location` attribute and thus makes sense
        #  only for Actors and Constructions (as of now)
        for item in neighbours.keys():
            line = self.get_line(location, item.location)
            if line[-1] == item.location and (len(line) > 2 or not exlcude_neighbours):
                neighbours[item] = len(line)
        r = list(sorted((x for x in neighbours.keys() if neighbours[x]), key=lambda x: neighbours[x]))
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
            # This is sorta ugly, but Dijkstras are rebuilt only when the queue starts processing and that happens
            # only at the turn's end. Thus, enemies act using outdated information (especially re:PC position)
            # Proper real-time queue might be better, but this thing is simple enough and does not require heavy
            # refactoring
            self.rebuild_dijkstras()
            for a in self.actors[1:]:
                a.make_turn()
            for a in self.constructions:
                a.make_turn()
        self.game_events.pass_all_events()
