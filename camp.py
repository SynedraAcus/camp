#! /usr/bin/env python3
#  Kivy imports
import kivy
kivy.require('1.9.0')
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock

#  Other imports
import sys

#  My own stuff
from Factories import TileWidgetFactory, MapFactory
from Actor import Actor

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
        #  Initializing keyboard bindings and key lists
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        #  Keys not in this list are ignored by _on_key_down
        self.allowed_keys=['spacebar', '.',
                           'w', 'a', 's', 'd',
                           'h', 'j', 'k', 'l',
                           'y', 'u', 'b', 'n',
                           'up', 'down', 'left', 'right',
                           'numpad1', 'numpad2', 'numpad3', 'numpad4', 'numpad5',
                           'numpad6', 'numpad7', 'numpad8', 'numpad9']
        #  Animation queue and stuff
        self.anim_queue = []
        self.block_keyboard = False

    def update_animation_queue(self, duration=0.3):
        """
        Populate self.anim_queue based on self.map.game_events
        :return:
        """
        for event in self.map.game_events:
            if event.event_type == 'moved':
                final = self._get_screen_pos(event.location)
                self.anim_queue.append((event.actor.widget,
                                       Animation(x=final[0], y=final[1], duration=duration)))
            elif event.event_type == 'attacked':
                #  Assuming that at the time of animation actor is still where he was during the attack
                #  Otherwise I'd have to support multiple locations for actors
                #  Attack animation is to move towards the target and then back
                current = self._get_screen_pos(event.actor.location)
                target = self._get_screen_pos(event.location)
                self.anim_queue.append((event.actor.widget,
                                        Animation(x=current[0]+int((target[0]-current[0])/2),
                                                  y=current[1]+int((target[1]-current[1])/2),
                                                  duration=duration/2)))
                self.anim_queue.append((event.actor.widget,
                                        Animation(x=current[0], y=current[1], duration=duration/2)))
            elif event.event_type == 'was_destroyed':
                self.anim_queue.append((event.actor.widget,
                                        Animation(size=(0, 0), duration=duration)))
                # self.map.delete_item(layer='actors', location=event.location)
        self.map.game_events = []

    def create_movement_animation(self, actor, duration=0.3):
        """
        Create the animation for actor movement, if it is not where it belongs. Pass otherwise.
        Tries to create animations for all actors (in case they were affected by the move),
        but to preserve chronological order moves the one in the argument first.
        :param actor:
        :param duration:
        :return:
        """
        final = self._get_screen_pos(actor.location)
        if not actor.widget.last_move_animated:
            self.anim_queue.append((actor.widget, Animation(x=final[0], y=final[1], duration=duration)))
            actor.widget.last_move_animated = True
        for other_actor in self.map.actors:
            if not other_actor is actor:
                final = self._get_screen_pos(other_actor.location)
                if not other_actor.widget.last_move_animated:
                    self.anim_queue.append((other_actor.widget,
                                            Animation(x=final[0], y=final[1], duration=duration)))
                    other_actor.widget.last_move_animated = True


        #  Animation flag
        self.animated_last_movement = False

    def remember_anim(self):
        self.block_keyboard = True

    def run_animation(self, widget=Widget()):
        """
        Recursive animation call for processing animation queue
        """
        if widget.size == (0, 0):
            #  If the widget was given zero size, this means it should be removed
            #  This entire affair, including creating placeholder widget on every iteration,
            #  is kinda inefficient and should be rebuilt later
            widget.parent.remove_widget(widget)
        if len(self.anim_queue)>0:
            widget, animation = self.anim_queue.pop(0)
            sys.stderr.write('Starting animation on {0}\n'.format(widget))
            animation.bind(on_start=lambda x, y: self.remember_anim(),
                           on_complete=lambda x, y: self.run_animation(y))  #  Second lambda arg is widget
            animation.start(widget)
        else:
            #  The queue is exhausted
            sys.stderr.write('Animation queue exhausted\n')
            self.block_keyboard = False

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
        #  Assumes self.map.actors[0] is player
        if self.block_keyboard:
            return
        if keycode[1] in self.allowed_keys and self.map.actors[0].controller.take_keycode(keycode):
            #  If this button is used, either by player controller or otherwise
            r = self.map.actors[0].make_turn()
            # self.create_movement_animation(self.map.actors[0])
            self.update_animation_queue()
            if r:
                #  If the player has managed to do something, draw results and let others work.
                #  If not for this check, the player attempting to do impossible things will have
                #  wasted a turn
                for actor in self.map.actors[1:]:
                    if actor.make_turn():
                        self.update_animation_queue()
                        # self.create_movement_animation(actor)
            #  Update log Label
            for x in self.parent.children:
                if x.id == 'log_window':
                    w = x
                    break
            w.text = '\n'.join(self.map.game_log[-3:])
            self.run_animation()

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard = None

    def update_rect(self, pos, size):
        self.rect.pos = self.pos
        self.rect.size = self.size

class LogWindow(Label):
    """ Text widget that shows the last 3 items from game_log
    """
    def __init__(self, *args, **kwargs):
        super(LogWindow, self).__init__(*args, **kwargs)
        with self.canvas.before:
            Color(1, 0, 0)
            Rectangle(size=self.size, pos=self.pos)

class CampApp(App):

    def build(self):
        root = BoxLayout(orientation='vertical')
        map_factory = MapFactory()
        map = map_factory.create_test_map()
        Window.size = (map.size[0]*64, map.size[1]*64+50)
        map_widget = RLMapWidget(map=map,
                                 size=(map.size[0]*64, map.size[1]*64),
                                 size_hint=(None, None),
                                 pos=(0, 100))

        root.add_widget(map_widget)
        log_widget = LogWindow(id='log_window',
                               text='\n'.join(map.game_log[-3:]),
                               size=(Window.size[0], 50),
                               pos=(0, 0),
                               #  Cannot use self.size here, as 'self' is a root widget
                               text_size=(Window.size[0], 50),
                               font_size=10,
                               valign='top',
                               line_height=1)
        root.add_widget(log_widget)
        return root

if __name__ == '__main__':
    CampApp().run()