#  This file contains various Factory classes for the Expedition Camp project

from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, BindTexture
from kivy.atlas import Atlas
from Map import RLMap, GroundTile, Actor

class ActorWidget(Widget):
    """
    The actor widget that contains an actor image
    """
    def __init__(self, texture=None, **kwargs):
        super(ActorWidget, self).__init__(**kwargs)
        self.img = Image(source='Tmp_frame_black.png', size=(64, 64))
        self.add_widget(self.img)
        self.bind(pos=self.update_img)
        # self.canvas.add(Rectangle(texture=texture))
        # t = CoreImage('Tmp_frame_black.png').texture
        # with self.canvas.after:
        #     BindTexture(texture=texture)
            # Rectangle(texture=texture, pos=self.pos, size=self.size)
            # self.rect = Rectangle(texture=texture, size=self.size, pos=self.pos)
            # self.bind(size=self.update_texture, pos=self.update_texture)

    def update_img(self, a, b):
        self.img.pos = self.pos

    def update_texture(self, size, pos):
        self.rect.size = self.size
        self.rect.pos = self.pos

class TileWidgetFactory(object):
    def __init__(self):
        self.atlas = Atlas('prototiles.atlas')
        self.atlas_texture=CoreImage('prototiles.png').texture

    def create_tile_widget(self, tile):
        if tile.passable:
            tile.widget = Image(source='Tmp_frame.png',
                                size_hint=(None, None),
                                size=(64, 64))
        return tile.widget

    def create_actor_widget(self, actor):
        widget = ActorWidget(texture=self.atlas.textures['PCproto'],
                                        size = (64, 64),
                                        size_hint=(None, None))
        # widget = Image(texture=self.atlas.textures['PC_proto'],
        #                size=(64,64),
        #                size_hint=(None, None))
        actor.widget = widget
        return widget

class MapFactory(object):
    def __init__(self):
        pass

    def create_test_map(self):
        map = RLMap(size=(10,10), layers=['bg', 'actors'])
        for x in range(10):
            for y in range(10):
                map.add_item(item=GroundTile(passable=True, image_source='Tmp_frame.png'),
                             layer='bg',
                             location=(x, y))
        map.add_item(item=Actor(player=False), location=(2, 2), layer='actors')
        map.add_item(item=Actor(player=True), location=(5,5), layer='actors')
        return map