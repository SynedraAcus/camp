#! /usr/bin/env python3
#  Kivy imports
import kivy
kivy.require('1.9.0')
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.audio import SoundLoader

#  Other imports
import sys

#  My own stuff
from Factories import TileWidgetFactory, MapFactory
from Actor import Actor
from Controller import Command


class KeyParser(object):
    """
    A class that contains methods for converting keycodes to Controller-compatible Commands, numbers
    and other interface commands. Keyboard layout is stored here as well.
    Currently class is little more than stub for later moving controls to separate file
    """
    #  Obsolete command dict, purely for reference
    command_dict = {'wait': ('spacebar', '.', 'numpad5'),
                #  Walking in cardinal directions
                'walk_8': ('w', 'h', 'numpad8', 'up'),
                'walk_2': ('s', 'l', 'numpad2', 'down'),
                'walk_4': ('a', 'j', 'numpad4', 'left'),
                'walk_6': ('d', 'k', 'numpad6', 'right'),
                #  Diagonal movement
                'walk_7': ('y', 'numpad7', ),
                'walk_9': ('u', 'numpad9', ),
                'walk_1': ('b', 'numpad1', ),
                'walk_3': ('n', 'numpad3', )}

    command_type_dict = {'walk': ('w', 'h', 'numpad8', 'up', # Up
                                  's', 'l', 'numpad2', 'down',
                                  'a', 'j', 'numpad4', 'left',
                                  'd', 'k', 'numpad6', 'right',
                                  'y', 'numpad7',  #NW
                                  'u', 'numpad9',  #NE
                                  'b', 'numpad1',  #SW
                                  'n', 'numpad3'), #SE
                         'wait': ('spacebar', '.', 'numpad5')}

    #  Values for travel commands are (dx, dy)
    #  For some commands value may be None, if there is no target associated with them
    command_value_dict = {(0, 1): ('w', 'h', 'numpad8', 'up'),
                          (0, -1): ('s', 'l', 'numpad2', 'down'),
                          (-1, 0): ('a', 'j', 'numpad4', 'left'),
                          (1, 0): ('d', 'k', 'numpad6', 'right'),
                          (-1, 1): ('y', 'numpad7'),
                          (1, 1): ('u', 'numpad9'),
                          (-1, -1): ('b', 'numpad1'),
                          (1, -1): ('n', 'numpad3'),
                          None: ('spacebar', '.', 'numpad5')}

    def __init__(self):
        self.command_types = {}
        self.command_values = {}
        #  Initializing commands
        for a in self.command_type_dict.items():
            self.command_types.update({x: a[0] for x in a[1]})
        for a in self.command_value_dict.items():
            self.command_values.update({x: a[0] for x in a[1]})

    @staticmethod
    def key_to_number(keycode):
        """
        Return a number that corresponds to this key. The number is passed to int() after optional numpad_ removed.
        ValueError is raised if key is not numerical
        :param keycode: kivy keycode
        :return:
        """
        if 'numpad' in keycode[1] or keycode[1] in '1234567890':
            return int(keycode[1][-1])
        else:
            raise ValueError('Non-numerical key passed to key_to_number')

    def key_to_command(self, keycode):
        """
        Return command that corresponds to a given keycode
        :param keycode:
        :return:
        """
        return Command(command_type=self.command_types[keycode[1]], command_value=self.command_values[keycode[1]])

class GameWidget(RelativeLayout):
    """
    Main game widget. Includes map, as well as various other widgets, as children.
    The game state is tracked by this widget's self.state
    """
    def __init__(self, map_widget=None, log_widget=None, **kwargs):
        super(GameWidget, self).__init__(**kwargs)
        self.map_widget = map_widget
        self.add_widget(self.map_widget)
        self.log_widget = log_widget
        self.add_widget(log_widget)
        #  Sound object
        self.boombox = {'moved': SoundLoader.load('dshoof.wav'),
                        'attacked': SoundLoader.load('dspunch.wav')}
        #  Keyboard controls
        #  Initializing keyboard bindings and key lists
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        #  Keys not in this list are ignored by _on_key_down
        self.allowed_keys = [#  Movement
                             'spacebar', '.',
                             'w', 'a', 's', 'd',
                             'h', 'j', 'k', 'l',
                             'y', 'u', 'b', 'n',
                             'up', 'down', 'left', 'right',
                             'numpad1', 'numpad2', 'numpad3', 'numpad4', 'numpad5',
                             'numpad6', 'numpad7', 'numpad8', 'numpad9', 'numpad0',
                             #  Window calls
                             'c', 'i',
                             #  Used for inventory & spell systems
                             '0', '1', '2', '3', '4', '5',
                             '6', '7', '8', '9']
        #  Keys in this list are processed by self.map_widget.map
        self.map_keys = ['spacebar', '.',
                         'w', 'a', 's', 'd',
                         'h', 'j', 'k', 'l',
                         'y', 'u', 'b', 'n',
                         'up', 'down', 'left', 'right',
                         'numpad1', 'numpad2', 'numpad3', 'numpad4', 'numpad5',
                         'numpad6', 'numpad7', 'numpad8', 'numpad9']
        self.key_parser = KeyParser()
        #  Game state
        self.game_state = 'playing'


    def _on_key_down(self, keyboard, keycode, text, modifier):
        """
        Process a single keypress
        :param keycode:
        :param text:
        :param modifier:
        :return:
        """
        #  Do nothing if animation is still running
        if self.map_widget.animating:
            return
        if keycode[1] in self.allowed_keys:
            #  Ignore unknown keys
            if self.game_state == 'playing':
                #  Either make a turn or show one of windows
                if keycode[1] in self.map_keys :
                    #  If the key is a 'map-controlling' one, ie uses a turn
                    command = self.key_parser.key_to_command(keycode)
                    self.map_widget.map.actors[0].controller.accept_command(command)
                    r = self.map_widget.map.actors[0].make_turn()
                    if r:
                        #  If the player has managed to do something, draw results and let others work.
                        #  If not for this check, the player attempting to do impossible things will have
                        #  wasted a turn
                        for actor in self.map_widget.map.actors[1:]:
                            actor.make_turn()
                    self.map_widget.process_game_event()
                elif keycode[1] in 'c':
                    #  Displaying player stats window
                    self.game_state = 'stat_window'
                    self.window_widget = LogWindow(pos=(200, 200),
                                                 size=(200, 200),
                                                 size_hint=(None, None),
                                                 text=self.map_widget.map.actors[0].descriptor.get_description(
                                                     combat=True))
                    self.add_widget(self.window_widget)
                elif keycode[1] in 'i':
                    self.game_state = 'inv_window'
                    self.window_widget = LogWindow(pos=(200, 200),
                                                   size=(200, 200),
                                                   size_hint=(None, None),
                                                   text=self.map_widget.map.actors[0].inventory.get_string())
                    self.add_widget(self.window_widget)
            else:
                if 'window' in self.game_state and keycode[1] in ('i', 'c'):
                    self.remove_widget(self.window_widget)
                    self.game_state = 'playing'
                elif self.game_state == 'inv_window':
                    #  Try to use keycode as inventory command
                    try:
                        n = self.key_parser.key_to_number(keycode)
                        #  Update inventory window
                        command = Command(command_type='use_item', command_value=(n, ))
                        self.map_widget.map.actors[0].controller.accept_command(command)
                        r = self.map_widget.map.actors[0].make_turn()
                        if r:
                            for actor in self.map_widget.map.actors[1:]:
                                actor.make_turn()
                        #  Remove inventory widget upon using item
                        self.remove_widget(self.window_widget)
                        self.game_state = 'playing'
                        #  Draw stuff
                        self.map_widget.process_game_event()
                    except ValueError:  #  This ValueError is expected to be raised by key_to_number if the keycode
                        #  is not numeric
                        pass


    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard = None

    def update_log(self):
        """
        Updating the log window under the map.
        :return:
        """
        pass
        self.log_widget.text = '\n'.join(self.map_widget.map.game_log[-3:])

#  Map widget (using RelativeLayout)
class RLMapWidget(RelativeLayout):
    """
    Game map widget. Mostly is busy displaying character widgets and such.
    Depends on its' parent having the following attributes:
    self.parent.boombox  a dict of SoundLoader instances with correct sounds
    and the following methods:
    self.parent.update_log()  Update the visible game log with this object's self.map.game_log
    """
    def __init__(self, map=None, **kwargs):
        super(FloatLayout, self).__init__(**kwargs)
        #  Connecting to map, factories and other objects this class should know about
        self.tile_factory = TileWidgetFactory()
        self.map = map
        self.size = [self.map.size[0]*64, self.map.size[1]*64]
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
        #  This is set to True during animation to avoid mistakes
        self.animating = False

#########################################################
    #
    #  Stuff related to animation
    #
########################################## ###############
    def process_game_event(self, widget=Widget(), anim_duration=0.3):
        """
        Process a single event from self.map.game_events.
        Read the event and perform the correct actions on widgets (such as update text of log window,
        create and launch animation, maybe make some sound). The event is removed from self.map.game_events.
        After the actions required are performed, the method calls itself again, either recursively, or, in
        case of animations, via Animation's on_complete argument. The recursion is broken when event queue is
        empty.
        :return:
        """
        if widget.size == (0, 0):
            #  If the widget was given zero size, this means it should be removed
            #  This entire affair, including creating placeholder widget on every iteration,
            #  is kinda inefficient and should be rebuilt later
            widget.parent.remove_widget(widget)
        if not self.map.game_events == []:
            event = self.map.game_events.pop(0)
            if event.event_type == 'moved':
                final = self._get_screen_pos(event.actor.location)
                a = Animation(x=final[0], y=final[1], duration=anim_duration)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.process_game_event(y))
                a.start(event.actor.widget)
            elif event.event_type == 'attacked':
                current = self._get_screen_pos(event.actor.location)
                target = self._get_screen_pos(event.location)
                a = Animation(x=current[0]+int((target[0]-current[0])/2),
                              y=current[1]+int((target[1]-current[1])/2),
                              duration=anim_duration/2)
                a += Animation(x = current[0], y=current[1], duration=anim_duration/2)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.process_game_event(y))
                a.start(event.actor.widget)
                self.parent.boombox['attacked'].play()
            elif event.event_type == 'was_destroyed':
                a = Animation(size=(0, 0), duration=anim_duration)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.process_game_event(y))
                a.start(event.actor.widget)
            elif event.event_type == 'log_updated':
                self.parent.update_log()
                self.process_game_event()
        else:
            #  Reactivating keyboard after finishing animation
            self.animating = False


    def remember_anim(self):
        '''
        This is a separate method because lambdas cannot into assignment, and animation queue
         depends on lambdas not to be evaluated prematurely.
        :return:
        '''
        self.animating = True

    def _get_screen_pos(self, location):
        """
        Return screen coordinates (in pixels) for a given location
        :param location: int tuple
        :return: int tuple
        """
        return (location[0]*64, location[1]*64)

############################################################
    #
    #  Keyboard-related methods
    #  The turn is made here, inside _on_key_down
    #
############################################################


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
                                 pos=(0, 50))
        log_widget = LogWindow(id='log_window',
                               text='\n'.join(map.game_log[-3:]),
                               size=(Window.size[0], 50),
                               size_hint=(None, None),
                               pos=(0, 0),
                               text_size=(Window.size[0], 50),
                               font_size=10,
                               valign='top',
                               line_height=1)
        game_widget = GameWidget(map_widget=map_widget,
                                 log_widget=log_widget,
                                 size=Window.size,
                                 size_hint=(None, None),
                                 pos=(0, 0))
        root.add_widget(game_widget)
        return root

if __name__ == '__main__':
    CampApp().run()