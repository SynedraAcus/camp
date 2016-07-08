#  This file contains various Factory classes for the Expedition Camp project

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
        s = 'Bottle.png'
        item.widget = ItemWidget(source=s, size=(32, 32),
                                 size_hint=(None, None))
        return item.widget

    def create_construction_widget(self, constr):
        constr.widget = ConstructionWidget(source=constr.image_source, size=(32, 32),
                                           size_hint=(None, None))
        return constr.widget


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
        map.add_item(item=Actor(player=True, controller=PlayerController(),
                                fighter=FighterComponent(),
                                descriptor=DescriptorComponent(name='PC',
                                                                description='Player-controlled dude'),
                                inventory=InventoryComponent(initial_items=[
                                    PotionTypeItem(
                                        name='Health Bottle 2|3',
                                        effect=FighterTargetedEffect(effect_type='heal',
                                                                     effect_value=[2, 3])),
                                    PotionTypeItem(
                                        name='Spawning flag',
                                        effect=TileTargetedEffect(effect_type='spawn_construction',
                                                                  map=map,
                                                                  effect_value=FighterConstruction(
                                                                      image_source='Headless.png',
                                                                      passable=False,
                                                                      fighter=FighterComponent(),
                                                                      faction=pc_faction,
                                                                      descriptor=DescriptorComponent(name='Headless dude'),
                                                                      controller=FighterSpawnController()),

                                                                  ))
                                ]),
                                faction = pc_faction,
                                image_source='PC.png'),
                     location=(5, 5), layer='actors')
        map.add_item(item=Actor(player=False, controller=AIController(),
                                fighter=FighterComponent(),
                                descriptor=DescriptorComponent(name='NPC2'),
                                faction=npc_faction,
                                inventory=InventoryComponent(volume=1,
                                                             initial_items=[PotionTypeItem(
                                                                 name='Bottle 2|3',
                                                                 effect=FighterTargetedEffect(effect_type='heal',
                                                                                              effect_value=[2,3])
                                                             )]),
                                image_source='NPC.png'),
                     location=(16, 16), layer='actors')
        map.add_item(item=PotionTypeItem(name='Health bottle 2|3',
                                         effect=FighterTargetedEffect(effect_type='heal',
                                                                      effect_value=[2, 3])),
                     location=(8, 5), layer='items')
        map.add_item(item=Spawner(image_source='DownStairs.png',
                                  faction=npc_faction),
                     location=(17, 17), layer='constructions')
        return map