#  This file contains various Factory classes for the Expedition Camp project

from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, BindTexture

#  Importing my own stuff
from Map import RLMap
from MapItem import GroundTile
from Actor import Actor
from Components import FighterComponent, DescriptorComponent, InventoryComponent
from Controller import PlayerController, AIController
from Items import PotionTypeItem
from Effects import FighterTargetedEffect

class ActorWidget(Widget):
    """
    The actor widget that contains an actor image
    """
    def __init__(self, source='PC.png', **kwargs):
        super(ActorWidget, self).__init__(**kwargs)
        self.img = Image(source=source, size=(64, 64), allow_stretch=True)
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
    """
    The tile widget that currently contains only an image.
    """
    def __init__(self, source='PC.png', **kwargs):
        super(TileWidget, self).__init__(**kwargs)
        self.img = Image(source=source, size=(64, 64))
        self.add_widget(self.img)
        self.bind(pos=self.update_img)

    def update_img(self, a, b):
        self.img.pos = self.pos

    def update_texture(self, size, pos):
        self.rect.size = self.size
        self.rect.pos = self.pos

class TileWidgetFactory(object):
    def __init__(self):
        pass

    def create_tile_widget(self, tile):
        s = 'Tile_passable.png' if tile.passable else 'Tile_impassable.png'
        tile.widget = TileWidget(source=s, size=(32, 32),
                                 size_hint=(None, None))
        return tile.widget

    def create_actor_widget(self, actor):
        s = 'PC.png' if actor.player else 'NPC.png'
        widget = ActorWidget(source=s, size=(32, 32),
                             size_hint=(None, None))
        actor.widget = widget
        return widget

class MapFactory(object):
    def __init__(self):
        pass

    def create_test_map(self):
        map = RLMap(size=(10, 10), layers=['bg', 'actors'])
        for x in range(10):
            map.add_item(item=GroundTile(passable=False, image_source='Tmp_frame.png'),
                         layer='bg',
                         location=(x, 0))
            map.add_item(item=GroundTile(passable=False, image_source='Tmp_frame.png'),
                         layer='bg',
                         location=(x, 9))
            for y in range(1, 9):
                map.add_item(item=GroundTile(passable=True, image_source='Tmp_frame.png'),
                             layer='bg',
                             location=(x, y))
        map.add_item(item=Actor(player=True, controller=PlayerController(),
                                fighter=FighterComponent(),
                                descriptor=DescriptorComponent(name='PC',
                                                                description='Player-controlled dude'),
                                inventory=InventoryComponent(initial_items=[PotionTypeItem(
                                    name='Health Bottle 2|3',
                                    effect=FighterTargetedEffect(effect_type='heal',
                                                                 effect_value=[2, 3]))])),
                     location=(5, 5), layer='actors')
        map.add_item(item=Actor(player=False, name='NPC1', controller=AIController(),
                                fighter=FighterComponent(),
                                descriptor=DescriptorComponent(name='NPC1')
                                ),
                     location=(2, 2), layer='actors')
        map.add_item(item=Actor(player=False, name='NPC2', controller=AIController(), fighter=FighterComponent(),
                                descriptor=DescriptorComponent(name='NPC2')),
                     location=(3, 5), layer='actors')
        return map