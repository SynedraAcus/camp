#  This file contains various Factory classes for the Expedition Camp project

from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.uix.widget import Widget
from kivy.graphics import Rectangle, BindTexture
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

    def update_img(self, a, b):
        self.img.pos = self.pos

    def update_texture(self, size, pos):
        self.rect.size = self.size
        self.rect.pos = self.pos

class TileWidgetFactory(object):
    def __init__(self):
        pass

    def create_tile_widget(self, tile):
        if tile.passable:
            tile.widget = Image(source='Tmp_frame.png',
                                size_hint=(None, None),
                                size=(64, 64))
        return tile.widget

    def create_actor_widget(self, actor):
        widget = ActorWidget(size = (64, 64),
                             size_hint=(None, None))
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
        map.add_item(item=Actor(player=True), location=(5,5), layer='actors')
        map.add_item(item=Actor(player=False), location=(2, 2), layer='actors')
        return map