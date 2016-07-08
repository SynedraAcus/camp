"""
Various factories, generating functions and other things.
Creates both Widgets and MapItems
"""

from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, BindTexture

#  Importing my own stuff
from Map import RLMap
from MapItem import GroundTile, MapItem
from Actor import Actor
from Constructions import Construction, FighterConstruction, Spawner
from Components import FighterComponent, DescriptorComponent, InventoryComponent, FactionComponent
from Controller import PlayerController, AIController, FighterSpawnController
from Items import PotionTypeItem, Item
from Effects import FighterTargetedEffect, TileTargetedEffect
from random import choice

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
        s = 'Tile_passable.png' if tile.passable else 'Tile_impassable.png'
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


def make_random_item():
    """
    Return a random item from a list defined inside the procedure.
    Some items cannot be created when map is not available, so a RLMap instance should be supplied
    :return:
    """
    items = [PotionTypeItem(name='Bottle',
                            effect=FighterTargetedEffect(effect_type='heal',
                                                         effect_value=[2, 3])),
             PotionTypeItem(name='Spawning flag',
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
                                                      )))]
    return choice(items)


class ActorFactory(object):
    """
    Factory that produces Actors of a given faction
    """
    def __init__(self, faction):
        assert isinstance(faction, FactionComponent)
        self.faction = faction

    def create_thug(self):
        """
        Creates a simple melee combatant. It has default FighterComponent
        and all the other components are (temporarily?) hardcoded
        :return:
        """
        return Actor(image_source='NPC.png',
                     controller=AIController(),
                     fighter=FighterComponent(),
                     descriptor=DescriptorComponent(name='A regular thug',
                                                    description='Not particularly smart, but also rarely alone'),
                     inventory=InventoryComponent(volume=1,
                                                  initial_items=[make_random_item()]),
                     faction=self.faction)


class MapFactory(object):
    def __init__(self):
        pass

    def create_test_map(self):
        map = RLMap(size=(20, 20), layers=['bg', 'constructions', 'items', 'actors'])
        for x in range(20):
            map.add_item(item=Construction(passable=False, image_source='Tree.png'),
                         layer='constructions',
                         location=(x, 0))
            map.add_item(item=Construction(passable=False, image_source='Tree.png'),
                         layer='constructions',
                         location=(x, 19))
            for y in range(20):
                map.add_item(item=GroundTile(passable=True, image_source='Tile_passable.png'),
                             layer='bg',
                             location=(x, y))
        #  Adding PC and NPCs
        pc_faction = FactionComponent(faction='pc', enemies=['npc'])
        npc_faction = FactionComponent(faction='npc', enemies=['pc'])
        thug_factory = ActorFactory(faction=npc_faction)
        map.add_item(item=Actor(controller=PlayerController(),
                                fighter=FighterComponent(),
                                descriptor=DescriptorComponent(name='PC',
                                                                description='Player-controlled dude'),
                                inventory=InventoryComponent(initial_items=[make_random_item(),
                                                                            make_random_item()]),
                                faction = pc_faction,
                                image_source='PC.png'),
                     location=(5, 5), layer='actors')
        map.add_item(thug_factory.create_thug(),
                     location=(16, 16), layer='actors')
        map.add_item(item=make_random_item(),
                     location=(8, 5), layer='items')
        map.get_item(location=(8, 5), layer='items').effect.map = map
        map.add_item(item=Spawner(image_source='DownStairs.png',
                                  faction=npc_faction,
                                  spawn_factory=thug_factory),
                     location=(17, 17), layer='constructions')
        return map