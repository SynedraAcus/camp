import kivy
kivy.require('1.9.0')
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle

from kivy.core.window import Window

from Factories import TileWidgetFactory, MapFactory
#  My own imports
from Map import RLMap, GroundTile

class PlaceholderActorWidget(Widget):
    pass

class GroudnTileWidget(Widget):
    pass

#  Map widget (using RelativeLayout)
class RLMapWidget(RelativeLayout):

    def __init__(self, map=None, **kwargs):
        super(FloatLayout, self).__init__(**kwargs)
        #  Connecting to map, factories and other objects this class should know about
        self.tile_factory = TileWidgetFactory()
        self.map = map
        #  Initializing tile widgets for BG layer and adding them as children
        for x in range(self.map.size[0]):
            for y in range(self.map.size[1]):
                tile_widget = self.tile_factory.create_tile_widget(self.map.get_item(layer='bg',
                                                                                    location=(x, y)))
                tile_widget.pos = self._get_screen_pos((x, y))
                self.add_widget(tile_widget)
        #  Initializing widgets for actor layers
        for x in range(self.map.size[0]):
            for y in range(self.map.size[1]):
                if self.map.has_item(layer='actors', location=(x, y)):
                    actor_widget = self.tile_factory.create_actor_widget(self.map.get_item(layer='actors',
                                 displayed                                                          location=(x, y)))
                    actor_widget.pos=(50*x, 50*y)
                    self.add_widget(actor_widget)
        #  Map background canvas. Used solely to test positioning
        with self.canvas.before:
            Color(0, 0, 1, 1)
            self.rect = Rectangle(size = self.size, pos=self.pos)
            self.bind(pos=self.update_rect, size=self.update_rect)
        #  Initializing keyboard bindings and key lists
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        #  The list of keys that will not be ignored by on_key_down
        self.used_keys=['w', 'a', 's', 'd']

    def redraw_actors(self):
        for actor in self.map.actors:
            actor.widget.pos = self._get_screen_pos(actor.location)

    def _get_screen_pos(self, location):
        """
        Return screen coordinates (in pixels) for a given location
        :param location: int tuple
        :return: int tuple
        """
        return (location[0]*50, location[1]*50)

    #  Keyboard-related methods

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        """
        Process keyboard event and make a turn, if necessary
        :param keyboard:
        :param keycode:
        :param text:
        :param modifiers:
        :return:
        """
        if keycode[1] in self.used_keys:
            self.map.process_turn(keycode)
            self.redraw_actors()

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard = None

    def update_rect(self, pos, size):
        self.rect.pos = self.pos
        self.rect.size = self.size


class CampApp(App):

    def build(self):
        root = FloatLayout()
        map_factory = MapFactory()
        map = map_factory.create_test_map()
        map_widget = RLMapWidget(map=map,
                                 size=(map.size[0]*50, map.size[1]*50),
                                 size_hint=(None, None))
        root.add_widget(map_widget)
        return root

if __name__ == '__main__':
    CampApp().run()