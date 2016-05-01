#! /usr/bin/env python3
#  Kivy imports
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
from kivy.animation import Animation
from kivy.clock import Clock

#  My own stuff
from Factories import TileWidgetFactory, MapFactory
from Map import RLMap, GroundTile


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
                                                                         location=(x, y)))
                    actor_widget.pos = self._get_screen_pos(location=(x, y))
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
        self.used_keys = ['w', 'a', 's', 'd', 'spacebar']
        #  Animation queue
        self.anim_queue = []

    def create_actor_animation(self, actor, duration):
        final = self._get_screen_pos(actor.location)
        return Animation(x=final[0], y=final[1], duration=duration)
        # a.start(actor.widget)

    def run_animation(self):
        """
        Recursive animation call
        """
        if self.anim_queue:
            widget, animation = self.anim_queue.pop(0)
            animation.bind(on_complete=lambda x,y: self.run_animation())
            # animation.bind(on_complete=lambda *args: print (args))
            animation.start(widget)

    def redraw_actors(self):
        for actor in self.map.actors:
            if not self._get_screen_pos(actor.location) == (actor.widget.x, actor.widget.y):
                self.anim_queue.append((actor.widget, self.create_actor_animation(actor, 0.5)))
        self.run_animation()


    def _get_screen_pos(self, location):
        """
        Return screen coordinates (in pixels) for a given location
        :param location: int tuple
        :return: int tuple
        """
        return (location[0]*64, location[1]*64)

    #  Keyboard-related methods

    def _on_key_down(self, keyboard, keycode, text, modifiers):
        """
        Process keyboard event and let all actors make turns. Basically this is a tick
        :param keyboard:
        :param keycode:
        :param text:
        :param modifiers:
        :return:
        """
        #  There are weird turn order bugs if the player is not the first element in map.actors
        if keycode[1] in self.used_keys:
            for actor in self.map.actors:
                if actor.player:
                    actor.pass_command(keycode)
                actor.make_turn()
                self.redraw_actors()
                # self.update_actor_widget(actor)

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
        Window.size=(map.size[0]*64, map.size[1]*64)
        map_widget = RLMapWidget(map=map,
                                 size=(map.size[0]*64, map.size[1]*64),
                                 size_hint=(None, None))
        root.add_widget(map_widget)
        return root

if __name__ == '__main__':
    CampApp().run()