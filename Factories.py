"""
Various factories, generating functions and other things.
Creates both Widgets and MapItems
"""

from kivy.uix.image import Image
from kivy.uix.widget import Widget

#  Importing my own stuff
from Map import RLMap
from MapItem import GroundTile, MapItem
from Actor import Actor
from Constructions import Construction, FighterConstruction, Spawner, Trap
from Components import *
from Controller import PlayerController, AIController, FighterSpawnController
from Items import PotionTypeItem, Item, FighterTargetedEffect, TileTargetedEffect

#  Other imports
from random import choice, randint
from copy import deepcopy


class ActorWidget(Widget):
    """
    The actor widget that contains an actor image
    """
    def __init__(self, source='PC.png', **kwargs):
        super(ActorWidget, self).__init__(**kwargs)
        self.img = Image(source=source, size=(32, 32), allow_stretch=True)
        self.add_widget(self.img)
        self.bind(pos=self.update_img)
        self.bind(size=self.update_img)
        # self.last_move_animated = True
        #  Flag that controls whether this widget is to be animated

    # def update_size(self, a, b):
    #     self.img.size=self.size

    def update_img(self, a, b):
        self.img.pos = self.pos
        self.img.size = self.size

    # def update_texture(self, size, pos):
    #     self.rect.size = self.size
    #     self.rect.pos = self.pos

class TileWidget(Widget):
    """widget
    The tile widget that currently contains only an image.
    """
    def __init__(self, source='PC.png', **kwargs):
        super(TileWidget, self).__init__(**kwargs)
        self.img = Image(source=source, size=(32, 32))
        self.add_widget(self.img)
        self.bind(pos=self.update_img)

    def update_img(self, a, b):
        self.img.pos = self.pos

    def update_texture(self, size, pos):
        self.rect.size = self.size
        self.rect.pos = self.pos

class ItemWidget(Widget):
    """
    Widget for an item. Used both for item on the ground and item in the inventory
    """
    def __init__(self, source='Bottle.png', **kwargs):
        super(ItemWidget, self).__init__(**kwargs)
        self.img = Image(source=source, size=(32, 32))
        self.add_widget(self.img)
        self.bind(pos=self.update_img)

    def update_img(self, a, b):
        self.img.pos = self.pos

class ConstructionWidget(Widget):
    """
    Widget for a construction
    """
    def __init__(self, source='DownStairs.png', **kwargs):
        super(ConstructionWidget, self).__init__(**kwargs)
        self.img = Image(source=source, size=(32, 32))
        self.add_widget(self.img)
        self.bind(pos=self.update_img)

    def update_img(self, a, b):
        self.img.pos = self.pos


class TileWidgetFactory(object):
    def __init__(self):
        # The dictionary that implements dispatching correct methods for any MapItem class
        self.type_methods = {GroundTile: self.create_tile_widget,
                             Actor: self.create_actor_widget,
                             Item: self.create_item_widget,
                             Construction: self.create_construction_widget}
        self.passable_tiles = ('Tile_passable.png',
                               'Tile_passable_2.png',
                               'Tile_passable_3.png')

    def create_widget(self, item):
        """
        Create a MapItem widget.
        Calls the correct method of self depending on what the class of MapItem is
        :param item:
        :return:
        """
        assert isinstance(item, MapItem)
        for t in self.type_methods.keys():
            if isinstance(item, t):
                return self.type_methods[t](item)

    def create_tile_widget(self, tile):
        s = choice(self.passable_tiles) if tile.passable else 'Tile_impassable.png'
        tile.widget = TileWidget(source=s, size=(32, 32),
                                 size_hint=(None, None))
        return tile.widget

    def create_actor_widget(self, actor):
        s = actor.image_source
        widget = ActorWidget(source=s, size=(32, 32),
                             size_hint=(None, None))
        actor.widget = widget
        return widget

    def create_item_widget(self, item):
        s = item.image_source
        item.widget = ItemWidget(source=s, size=(32, 32),
                                 size_hint=(None, None))
        return item.widget

    def create_construction_widget(self, constr):
        constr.widget = ConstructionWidget(source=constr.image_source, size=(32, 32),
                                           size_hint=(None, None))
        return constr.widget


class ItemFactory:
    """
    A factory for the inventory items.
    :return:
    """
    items = [PotionTypeItem(descriptor=DescriptorComponent(name='Bottle',
                                                           description='Heals for 2 or 3 HP'),
                            effect=FighterTargetedEffect(effect_type='heal',
                                                         effect_value=[2, 3])),
             PotionTypeItem(descriptor=DescriptorComponent(name='Spawning flag',
                                                           description='Builds a headless dude under the player'),
                            image_source='Flag.png',
                            effect=TileTargetedEffect(effect_type='spawn_construction',
                                                      map=None,
                                                      effect_value=FighterConstruction(
                                                          passable=False,
                                                          image_source='Headless.png',
                                                          fighter=FighterComponent(),
                                                          faction=FactionComponent(faction='pc',
                                                                                   enemies=['npc']),
                                                          descriptor=DescriptorComponent(name='Headless dude'),
                                                          controller=FighterSpawnController(),
                                                      ))),
             PotionTypeItem(descriptor=DescriptorComponent(name='Landmine',
                                                           description='Places a landmine under the player'),
                            image_source='Landmine.png',
                            effect=TileTargetedEffect(effect_type='spawn_construction',
                                                      map=None,
                                                      effect_value=Trap(image_source='Mined.png',
                                                                        effect=TileTargetedEffect(
                                                                            effect_type='explode',
                                                                            effect_value=5)))),
             PotionTypeItem(descriptor=DescriptorComponent(name='Rocket',
                                                           description='Can and should be [F]ired at enemies'),
                            image_source='Rocket.png',
                            effect=TileTargetedEffect(effect_type='explode', effect_value=5))
             ]

    def create_random(self):
        """
        Return a random item from self.items
        :return: Item instance
        """
        return deepcopy(choice(self.items))

    def give_all(self):
        """
        Return a list containing a single copy of all available items
        :return:
        """
        return deepcopy(self.items)


class MapItemDepot():
    """
    A class that contains definitions of every item that can be placed on map during map generation.
    Every make_* method returns the instance of object in question.
    """


    def __init__(self):
        self.item_factory = ItemFactory()
        self.item_methods = [self.make_landmine,
                             self.make_bottle,
                             self.make_flag,
                             self.make_rocket]
        self.glyph_methods = {'#': self.make_wall,
                              'S': self.make_spawner,
                              '^': self.make_mine,
                              'f': self.make_fighter,
                              '_': self.make_hole,
                              '@': self.make_pc,
                              'z': self.make_thug,
                              'R': self.make_rocket,
                              'L': self.make_landmine,
                              'B': self.make_bottle,
                              'F': self.make_flag}

    def make_pc(self):
        """
        Player character
        :return:
        """
        return Actor(image_source='PC.png',
                     controller=PlayerController(),
                     fighter=FighterComponent(),
                     inventory=InventoryComponent(volume=10, initial_items=self.get_all_items()),
                     faction=FactionComponent(faction='pc', enemies=['npc']),
                     descriptor=DescriptorComponent(name='PC', description='Player character'),
                     breath=BreathComponent())

    @staticmethod
    def make_wall():
        """
        Impassable wall
        :return:
        """
        return Construction(image_source='Tree.png', passable=False,
                            descriptor=DescriptorComponent(name='Tree'))

    @staticmethod
    def make_spawner():
        """
        Thug spawner
        :return:
        """
        return Spawner(image_source='DownStairs.png', spawn_frequency=3,
                       spawn_factory=ActorFactory(faction=FactionComponent(faction='pc',
                                                                           enemies=['npc'])),
                       faction=FactionComponent(faction='pc', enemies=['npc']),
                       descriptor=DescriptorComponent(name='A dark hole in the ground'))

    @staticmethod
    def make_mine():
        """
        Landmine (the construction)
        :return:
        """
        return Trap(effect=TileTargetedEffect(effect_type='explode', effect_value=5),
                    image_source='Mined.png')

    @staticmethod
    def make_hole():
        """
        Explosion-produced hole
        :return:
        """
        return Construction(image_source='Hole.png', passable=False)

    @staticmethod
    def make_fighter():
        """
        Headless dude
        :return:
        """
        return Construction(image_source='Headless.png', passable=False,
                            fighter=FighterComponent(),
                            faction=FactionComponent(faction='pc', enemies=['npc']),
                            descriptor=DescriptorComponent(name='Headless dude',
                                                           description='It fights on your side'),
                            controller=FighterSpawnController())

    def make_thug(self):
        """
        A regular thug
        :return:
        """
        return Actor(image_source='NPC.png',
                     controller=AIController(),
                     fighter=FighterComponent(max_hp=2),
                     descriptor=DescriptorComponent(name='PC',
                                                    description='Player character'),
                     inventory=InventoryComponent(volume=1,
                                                  initial_items=[self.make_random_item()]),
                     faction=FactionComponent(faction='npc', enemies=['pc']))

    @staticmethod
    def make_rocket():
        """
        Rocket
        :return:
        """
        return PotionTypeItem(descriptor=DescriptorComponent(name='Rocket',
                                                             description='Can and should be [F]ired at enemies'),
                              image_source='Rocket.png',
                              effect=TileTargetedEffect(effect_type='explode', effect_value=5))

    @staticmethod
    def make_landmine():
        """
        Landmine (item)
        :return:
        """
        return PotionTypeItem(descriptor=DescriptorComponent(name='Landmine',
                                                             description='Places a landmine under the player'),
                              image_source='Landmine.png',
                              effect=TileTargetedEffect(effect_type='spawn_construction',
                                                        map=None,
                                                        effect_value=Trap(image_source='Mined.png',
                                                                          effect=TileTargetedEffect(
                                                                            effect_type='explode',
                                                                            effect_value=5))))

    @staticmethod
    def make_bottle():
        """
        Bottle
        :return:
        """
        return PotionTypeItem(descriptor=DescriptorComponent(name='Bottle',
                                                             description='Heals for 2 or 3 HP'),
                              image_source='Bottle.png',
                              effect=FighterTargetedEffect(effect_type='heal',
                                                           effect_value=[2, 3]))

    @staticmethod
    def make_flag():
        """
        Spawning flag
        :return:
        """
        return PotionTypeItem(descriptor=DescriptorComponent(name='Spawning flag',
                                                             description='Builds a headless dude under the player'),
                              image_source='Flag.png',
                              effect=TileTargetedEffect(effect_type='spawn_construction',
                                                        map=None,
                                                        effect_value=FighterConstruction(
                                                          passable=False,
                                                          image_source='Headless.png',
                                                          fighter=FighterComponent(),
                                                          faction=FactionComponent(faction='pc',
                                                                                   enemies=['npc']),
                                                          descriptor=DescriptorComponent(name='Headless dude'),
                                                          controller=FighterSpawnController()
                                                         )))

    #  Following methods generate items according to some rule

    def make_random_item(self):
        """
        Create a random item
        :return:
        """
        method = choice(self.item_methods)
        i = method()
        return i

    def get_all_items(self):
        r = []
        for method in self.item_methods:
            r.append(method())
        return r

    def get_item_by_glyph(self, glyph):
        """
        Return the item encoded by the glyph
        :param glyph:
        :return:
        """
        method = self.glyph_methods[glyph]
        item = method()
        return item


class MapLoader():
    """
    The map file interface. It takes a filehandle and returns a complete map. Everything it needs to do so is not
    the caller's problem.
    """
    def __init__(self):
        #  A dict of tag-to-function mappings. Values should be callables that accept string a return an object of
        #  required type
        self.tag_converters = {'height': int,
                               'width': int,
                               'aesthetic': str}

        self.map_values = {'#': Construction(image_source='Tree.png', passable=False,
                                             descriptor=DescriptorComponent(name='Tree')),
                           '@': Actor(controller=PlayerController(),
                                      fighter=FighterComponent(),
                                      inventory=InventoryComponent(volume=10),
                                      faction=FactionComponent(faction='pc', enemies=['npc']),
                                      breath=BreathComponent(),
                                      descriptor=DescriptorComponent(name='PC',
                                                                     description='Player character'),
                                      image_source='PC.png'),
                           'S': Spawner(image_source='DownStairs.png',
                                        spawn_factory = None)}
        self.layers = {'#': 'constructions',
                       '@': 'actors',
                       'S': 'constructions'}

    def parse_tag_line(self, line):
        """
        Parse a tag line
        Convert the value to the required type (as per tag_types) and return (key, value) pair
        :param line:
        :return:
        """
        line = line.lstrip('/')
        a = line.split()
        if len(a) == 2:
            try:
                r = a[0], self.tag_converters[a[0]](a[1])
            except KeyError:
                raise ValueError('Unknown tag {0} in the map file'.format(a[0]))
        else:
            raise ValueError('Incorrect tag line "{0}"'.format(line))
        return r

    def read_map_file(self, handle):
        """
        Read a file that contains a single map
        :param handle: filehandle to a *.lvl file
        :return:
        """
        tags = {}
        map_lines = []
        reading_map = False
        for line in handle:
            if line[0]=='/':
                if reading_map:
                    #  Only read tags *before* the map
                    break
                l = self.parse_tag_line(line)
                tags.update({l[0]: l[1]})
            else:
                map_lines.append(line)
                reading_map = True
        # print(tags)
        # print('\n'.join(map_lines))
        map = RLMap(size=(tags['width'], tags['height']), layers=['bg', 'constructions', 'items', 'actors'])
        for y in range(0, tags['height']):
            for x in range(0, tags['width']):
                map.add_item(GroundTile(passable=True, image_source='Tile_passable.png'),
                             layer='bg', location=(x,y))
                i = map_lines[y][x]
                if i == '.':
                    #  Nothing to place here
                    continue
                item = self.map_values[i]
                map.add_item(item=self.map_values[i],
                             layer=self.layers[i],
                             location=(x,y))
                # if i == '@':
                #     map.actors.insert(0, item)
        return map


class ActorFactory(object):
    """
    Factory that produces Actors of a given faction
    """
    def __init__(self, faction):
        assert isinstance(faction, FactionComponent)
        self.faction = faction
        self.item_factory = ItemFactory()

    def create_thug(self):
        """
        Creates a simple melee combatant. It has default FighterComponent
        and all the other components are (temporarily?) hardcoded
        :return:
        """
        return Actor(image_source='NPC.png',
                     controller=AIController(),
                     fighter=FighterComponent(max_hp=2),
                     descriptor=DescriptorComponent(name='PC',
                                                    description='Player character'),
                     inventory=InventoryComponent(volume=1,
                                                  initial_items=[self.item_factory.create_random()]),
                     faction=self.faction)


class MapFactory(object):
    def __init__(self):
        self.map_loader = MapLoader()

    def load_map(self, map_file):
        """
        Call a MapLoader instance to load a map from file. Assumes the file to contain a single map
        :param map_file:
        :return:
        """
        return self.map_loader.read_map_file(open(map_file))

    def create_test_map(self):
        """
        A basic map generator. Places a single enemy spawner and several items.
        :return:
        """
        depot = MapItemDepot()
        map = RLMap(size=(20, 15), layers=['bg', 'constructions', 'items', 'actors'])
        for x in range(20):
            #  Background
            for y in range(15):
                map.add_item(item=GroundTile(passable=True, image_source='Tile_passable.png'),
                             layer='bg',
                             location=(x, y))
            #  Adding trees along border
            map.add_item(item=depot.make_wall(),
                         layer='constructions',
                         location=(x, 0))
            map.add_item(item=depot.make_wall(),
                         layer='constructions',
                         location=(x, 14))
        for x in range(15):
            map.add_item(item = depot.make_wall(),
                         layer='constructions',
                         location = (x, 7))
        #  Adding PC and NPCs
        item_factory = ItemFactory()
        map.add_item(depot.make_pc(),
                     location=(2, 2), layer='actors')
        map.add_item(item=depot.make_spawner(),
                     location=(2, 13), layer='constructions')
        map.add_item(item=depot.make_thug(),
                     location=(4,12), layer='actors')
        #  Add 7 items in free tiles. Tiles with actors are considered free for this purpose
        for a in range(7):
            while True:
                pos = (randint(0, map.size[0]-1), randint(0, map.size[1]-1))
                if not map.get_item(layer='items', location=pos)\
                        and not map.get_item(layer='constructions', location=pos):
                    map.add_item(item=depot.make_random_item(),
                                 location=pos, layer='items')
                    # map.get_item(location=pos, layer='items').effect.map = map
                    break
        #  Update Dijkstra maps
        map.update_dijkstra()
        return map