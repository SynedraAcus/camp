"""
The classes responsible for loading levels from files. This file is supposed to be imported by Factories.py and
 nobody else
"""
from Actor import Actor
from Components import *
from Constructions import Construction, Spawner
from Controller import PlayerController
from Map import RLMap
from MapItem import GroundTile


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
