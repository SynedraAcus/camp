#! /usr/bin/env python3
#  Kivy imports
import kivy
kivy.require('1.9.0')
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.core.audio import SoundLoader

#  My own stuff
from Factories import TileWidgetFactory, MapFactory
from Controller import Command

#  Other imports
import threading

#  A collection of constants. Most definitely needs to be refactored into a proper option container

#  Whether to display Dijkstra map values overlay. Extremely laggy and should be False unless debugging
#  Dijkstra maps
DISPLAY_DIJKSTRA_MAP = False

class KeyParser(object):
    """
    A class that contains methods for converting keycodes to Controller-compatible Commands, numbers
    and other interface commands. Keyboard layout is stored here as well.
    Currently class is little more than stub for later moving controls to separate file
    """
    #  Obsolete human-readable command dict, actually not used by any methods.
    #  Kept purely for reference.
    command_dict = {'wait': ('spacebar', '.', 'numpad5'),
                #  Walking in cardinal directions
                'walk_8': ('h', 'numpad8', 'up'),
                'walk_2': ('l', 'numpad2', 'down'),
                'walk_4': ('j', 'numpad4', 'left'),
                'walk_6': ('k', 'numpad6', 'right'),
                #  Diagonal movement
                'walk_7': ('y', 'numpad7', ),
                'walk_9': ('u', 'numpad9', ),
                'walk_1': ('b', 'numpad1', ),
                'walk_3': ('n', 'numpad3', ),
                'grab': (',', 'g')}

    command_type_dict = {'walk': ('h', 'numpad8', 'up', # Up
                                  'l', 'numpad2', 'down',
                                  'j', 'numpad4', 'left',
                                  'k', 'numpad6', 'right',
                                  'y', 'numpad7',  #NW
                                  'u', 'numpad9',  #NE
                                  'b', 'numpad1',  #SW
                                  'n', 'numpad3'), #SE
                         'wait': ('spacebar', '.', 'numpad5'),
                         'grab': ('g', ','),
                         'drop': ('d')}

    #  Values for travel commands are (dx, dy)
    #  Values for inventory use and drop are not kept here, as those are used from window
    #  For some commands value may be None, if there is no target associated with them
    command_value_dict = {(0, 1): ('w', 'h', 'numpad8', 'up'),
                          (0, -1): ('s', 'l', 'numpad2', 'down'),
                          (-1, 0): ('a', 'j', 'numpad4', 'left'),
                          (1, 0): ('d', 'k', 'numpad6', 'right'),
                          (-1, 1): ('y', 'numpad7'),
                          (1, 1): ('u', 'numpad9'),
                          (-1, -1): ('b', 'numpad1'),
                          (1, -1): ('n', 'numpad3'),
                          None: ('spacebar', '.', 'numpad5', 'g', ',')}

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
                        'attacked': SoundLoader.load('dspunch.wav'),
                        'exploded': SoundLoader.load('dsbarexp.wav')}
        #  Sound in kivy seems to be loaded lazily. IE files are not actually read until they are necessary,
        #  which leads to lags for up to half a second (on my computer at least). The following two lines are
        #  forcing it to be read right now.
        for sound in self.boombox.keys():
            self.boombox[sound].seek(0)
        #  Keyboard controls
        #  Initializing keyboard bindings and key lists
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_key_down)
        #  Keys not in this list are ignored by _on_key_down
        self.allowed_keys = [#  Movement
                             'spacebar', '.',
                             'h', 'j', 'k', 'l',
                             'y', 'u', 'b', 'n',
                             'up', 'down', 'left', 'right',
                             'numpad1', 'numpad2', 'numpad3', 'numpad4', 'numpad5',
                             'numpad6', 'numpad7', 'numpad8', 'numpad9', 'numpad0',
                             #  Window calls
                             'c', 'i',
                             #  Used for inventory & spell systems
                             '0', '1', '2', '3', '4', '5',
                             '6', '7', '8', '9',
                             #  Grabbing and dropping stuff
                             'g', ',', 'd',
                             #  Jumping
                             'z']
        #  Keys in this list are processed by self.map_widget.map
        self.map_keys = ['spacebar', '.',
                         'h', 'j', 'k', 'l',
                         'y', 'u', 'b', 'n',
                         'up', 'down', 'left', 'right',
                         'numpad1', 'numpad2', 'numpad3', 'numpad4', 'numpad5',
                         'numpad6', 'numpad7', 'numpad8', 'numpad9',
                         'g', ',']
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
                if keycode[1] in self.map_keys:
                    #  If the key is a 'map-controlling' one, ie uses a turn without calling windows
                    command = self.key_parser.key_to_command(keycode)
                    self.map_widget.map.actors[0].controller.accept_command(command)
                    r = self.map_widget.map.actors[0].make_turn()
                    if r:
                        #  If the player has managed to do something, draw results and let others work.
                        #  If not for this check, the player attempting to do impossible things will have
                        #  wasted a turn
                        for actor in self.map_widget.map.actors[1:]:
                            actor.make_turn()
                        for construction in self.map_widget.map.constructions:
                            construction.make_turn()
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
                elif keycode[1] in 'd':
                    self.game_state = 'drop_window'
                    self.window_widget = LogWindow(pos=(200, 200),
                                                   size=(200, 200),
                                                   size_hint=(None, None),
                                                   text=self.map_widget.map.actors[0].inventory.get_string())
                    self.add_widget(self.window_widget)
                elif keycode[1] in 'z':
                    self.game_state = 'jump_targeting'
                    self.target_coordinates = self.map_widget.map.actors[0].location
                    self.window_widget = Image(source='Mined.png',
                                               pos=self.map_widget.get_screen_pos(self.target_coordinates,
                                                                                  parent=True),
                                               size=(32, 32),
                                               size_hint=(None, None))
                    self.add_widget(self.window_widget)
            else:
                if 'window' in self.game_state and keycode[1] in ('i', 'c', 'g', 'd'):
                    self.remove_widget(self.window_widget)
                    self.game_state = 'playing'
                elif self.game_state == 'inv_window':
                    #  Try to use keycode as inventory command
                    try:
                        n = self.key_parser.key_to_number(keycode)
                        command = Command(command_type='use_item', command_value=(n, ))
                        self.map_widget.map.actors[0].controller.accept_command(command)
                        r = self.map_widget.map.actors[0].make_turn()
                        if r:
                            for actor in self.map_widget.map.actors[1:]:
                                actor.make_turn()
                            for construction in self.map_widget.map.constructions:
                                construction.make_turn()
                        #  Remove inventory widget upon using item
                        self.remove_widget(self.window_widget)
                        self.game_state = 'playing'
                        #  Draw stuff
                        self.map_widget.process_game_event()
                    except ValueError:  #  This ValueError is expected to be raised by key_to_number if the keycode
                        #  is not numeric
                        pass
                elif self.game_state == 'drop_window':
                    #  Try to use keycode as inventory command
                    try:
                        n = self.key_parser.key_to_number(keycode)
                        command = Command(command_type='drop_item', command_value=(n, ))
                        self.map_widget.map.actors[0].controller.accept_command(command)
                        r = self.map_widget.map.actors[0].make_turn()
                        if r:
                            for actor in self.map_widget.map.actors[1:]:
                                actor.make_turn()
                            for construction in self.map_widget.map.constructions:
                                construction.make_turn()
                        #  Remove inventory widget upon using item
                        self.remove_widget(self.window_widget)
                        self.game_state = 'playing'
                        #  Draw stuff
                        self.map_widget.process_game_event()
                    except ValueError:
                        pass
                elif 'targeting' in self.game_state:
                    if keycode[1] in 'z':
                        delta = (self.target_coordinates[0]-self.map_widget.map.actors[0].location[0],
                                 self.target_coordinates[1]-self.map_widget.map.actors[0].location[1])
                        command = Command(command_type='walk', command_value=delta)
                        self.map_widget.map.actors[0].controller.accept_command(command)
                        self.map_widget.map.actors[0].make_turn()
                        self.map_widget.process_game_event()
                    elif self.key_parser.command_types[keycode[1]] == 'walk':
                        #  Move the targeting widget
                        delta = self.key_parser.command_values[keycode[1]]
                        self.target_coordinates = [self.target_coordinates[0]+delta[0],
                                                   self.target_coordinates[1]+delta[1]]
                        self.window_widget.pos = self.map_widget.get_screen_pos(self.target_coordinates,
                                                                                parent=True)





    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_key_down)
        self._keyboard = None

    def update_log(self):
        """
        Updating the log window under the map.
        :return:
        """
        if len(self.map_widget.map.game_log) > 6:
            self.log_widget.text = '\n'.join(self.map_widget.map.game_log[-6:])
        else:
            self.log_widget.text = '\n'.join(self.map_widget.map.game_log)


class LayerWidget(RelativeLayout):
    """
    A map layer widget.
    Displays a single layer of a map: items, or actors, or bg, or something.
    Depends on its parent having the following attributes:
    self.parent.map  a Map instance with a layer corresponding to this widget
    tile_factory  a TileWidgetFactory instance
    """
    def __init__(self, layer='layer', parent=None, **kwargs):
        super(LayerWidget, self).__init__(**kwargs)
        self.layer = layer
        #  Parent is used only temporarily in a constructor.
        #  When the widget is in use, it'll be self.parent, but the widget cannot be attached before
        #  it is constructed
        self.size = parent.size
        #  Initializing tile widgets
        for x in range(parent.map.size[0]):
            for y in range(parent.map.size[1]):
                item = parent.map.get_item(layer=self.layer, location=(x, y))
                if item:
                    tile_widget = parent.tile_factory.create_widget(
                        parent.map.get_item(layer=self.layer,
                                            location=(x, y))
                                    )
                    tile_widget.pos = parent.get_screen_pos((x, y))
                    self.add_widget(tile_widget)

class DijkstraWidget(RelativeLayout):
    """
    The widget that displays little numbers on every tile to allow debugging Dijkstra maps.
    This widget is designed to be a child of RLMapWidget, so it relies on its methods
    For such a crude testing thing I won't even write updating: let's just remove it and create
    anew every time Dijkstra map is updated. Therefore it's immensely laggy and performance of anything
    should be tested with it disabled.
    """
    def __init__(self, parent = None, **kwargs):
        super(DijkstraWidget, self).__init__(**kwargs)
        for x in range(parent.map.size[0]):
            for y in range(parent.map.size[1]):
                self.add_widget(Label(size=(64, 64),
                                      size_hint=(None,None),
                                      pos=parent.get_screen_pos((x, y)),
                                      text=str(parent.map.dijkstra[x][y]),
                                      text_size=(64, 64),
                                      font_size=7))

class RLMapWidget(RelativeLayout):
    """
    Game map widget. Mostly is busy displaying character widgets and such.
    Depends on its parent having the following attributes:
    self.parent.boombox  a dict of SoundLoader instances with correct sounds
    and the following methods:
    self.parent.update_log()  Update the visible game log with this object's self.map.game_log
    """
    def __init__(self, map=None, **kwargs):
        super(RLMapWidget, self).__init__(**kwargs)
        #  Connecting to map, factories and other objects this class should know about
        self.tile_factory = TileWidgetFactory()
        self.map = map
        self.size = [self.map.size[0]*32, self.map.size[1]*32]
        #  Adding LayerWidgets for every layer of the map
        self.layer_widgets = {}
        for layer in self.map.layers:
            self.layer_widgets.update({layer: LayerWidget(layer=layer, parent=self)})
            self.add_widget(self.layer_widgets[layer])
        #  This is set to True during animation to avoid mistakes
        self.animating = False
        #  A temporary widget slot for stuff like explosions, spell effects and such
        self.overlay_widget = None
        #  Debugging Dijkstra map view
        if DISPLAY_DIJKSTRA_MAP:
            self.dijkstra_widget = DijkstraWidget(parent=self)
            self.add_widget(self.dijkstra_widget)

#########################################################
    #
    #  Stuff related to animation
    #
########################################## ###############label
    def process_game_event(self, widget=None, anim_duration=0.3):
        """
        Process a single event from self.map.game_events.
        Read the event and perform the correct actions on widgets (such as update text of log window,
        create and launch animation, maybe make some sound). The event is removed from self.map.game_events.
        After the actions required are performed, the method calls itself again, either recursively, or, in
        case of animations, via Animation's on_complete argument. The recursion is broken when event queue is
        empty.
        :return:
        """
        if widget and widget.parent and widget.height < 1:
            #  If the widget was given zero size, this means it should be removed
            #  This entire affair, including creating placeholder widget on every iteration,
            #  is kinda inefficient and should be rebuilt later
            widget.parent.remove_widget(widget)
        if not self.map.game_events == []:
            event = self.map.game_events.pop(0)
            if event.event_type == 'moved':
                final = self.get_screen_pos(event.actor.location)
                a = Animation(x=final[0], y=final[1], duration=anim_duration)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.process_game_event(widget=y))
                a.start(event.actor.widget)
            elif event.event_type == 'attacked':
                current = self.get_screen_pos(event.actor.location)
                target = self.get_screen_pos(event.location)
                a = Animation(x=current[0]+int((target[0]-current[0])/2),
                              y=current[1]+int((target[1]-current[1])/2),
                              duration=anim_duration/2)
                a += Animation(x=current[0], y=current[1], duration=anim_duration/2)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.process_game_event(widget=y))
                a.start(event.actor.widget)
                self.parent.boombox['attacked'].play()
            elif event.event_type == 'was_destroyed':
                a = Animation(size=(0, 0), duration=anim_duration)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.process_game_event(widget=y))
                a.start(event.actor.widget)
            elif event.event_type == 'log_updated':
                self.parent.update_log()
                self.process_game_event()
            elif event.event_type == 'picked_up':
                #  It's assumed that newly added item will be the last in player inventory
                self.layer_widgets['items'].remove_widget(self.map.actors[0].inventory[-1].widget)
                self.process_game_event()
            elif event.event_type == 'dropped':
                item = self.map.get_item(location=event.location, layer='items')
                if not item.widget:
                    self.tile_factory.create_widget(item)
                    item.widget.pos = self.get_screen_pos(event.location)
                self.layer_widgets['items'].add_widget(item.widget)
                self.process_game_event()
            elif event.event_type == 'actor_spawned':
                a = event.actor
                if not a.widget:
                    self.tile_factory.create_widget(a)
                    a.widget.pos = self.get_screen_pos(event.location)
                self.layer_widgets['actors'].add_widget(a.widget)
                self.process_game_event()
            elif event.event_type == 'construction_spawned':
                a = event.actor
                if not a.widget:
                    self.tile_factory.create_widget(a)
                    a.widget.pos = self.get_screen_pos(event.location)
                self.layer_widgets['constructions'].add_widget(a.widget)
                self.process_game_event()
            elif event.event_type == 'exploded':
                loc = self.get_screen_pos(event.location)
                loc = (loc[0]+16, loc[1]+16)
                self.overlay_widget = Image(source='Explosion.png',
                                            size=(0, 0),
                                            size_hint=(None, None),
                                            pos=loc)
                a = Animation(size=(96, 96), pos=(loc[0]-32, loc[1]-32),
                              duration=anim_duration)
                a += Animation(size=(0, 0), pos=loc,
                               duration=anim_duration)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.process_game_event(widget=y))
                self.add_widget(self.overlay_widget)
                self.parent.boombox['exploded'].play()
                a.start(self.overlay_widget)
        else:
            #  Reactivating keyboard after finishing animation
            self.animating = False
            #  Might as well be time to redraw the Dijkstra widget
            if DISPLAY_DIJKSTRA_MAP:
                self.remove_widget(self.dijkstra_widget)
                self.dijkstra_widget = DijkstraWidget(parent=self)
                self.add_widget(self.dijkstra_widget)

    def remember_anim(self):
        '''
        This is a separate method because lambdas cannot into assignment, and animation queue
         depends on lambdas not to be evaluated prematurely.
        :return:
        '''
        self.animating = True

    def get_screen_pos(self, location, parent=False):
        """
        Return screen coordinates (in pixels) for a given location. Unless window parameter is set to true,
        returns coordinates relative to self
        :param location: int tuple
        :param window: bool If true, return window coordinates.
        :return: int tuple
        """
        if not parent:
            return (location[0]*32, location[1]*32)
        else:
            return(self.to_parent(location[0]*32, location[1]*32))

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
    """
    Main app class.
    """
    def build(self):
        root = BoxLayout(orientation='vertical')
        map_factory = MapFactory()
        map = map_factory.create_test_map()
        map_widget = RLMapWidget(map=map,
                                 size=(map.size[0]*32, map.size[1]*32),
                                 size_hint=(None, None),
                                 pos=(0, 100))
        log_widget = LogWindow(id='log_window',
                               text='\n'.join(map.game_log[-3:]),
                               size=(map_widget.width, 100),
                               size_hint=(None, None),
                               pos=(0, 0),
                               text_size=(map_widget.width, 100),
                               padding=(20, 5),
                               font_size=10,
                               valign='top',
                               line_height=1)
        Window.size = (map_widget.width, map_widget.height+log_widget.height)
        game_widget = GameWidget(map_widget=map_widget,
                                 log_widget=log_widget,
                                 size=Window.size,
                                 size_hint=(None, None),
                                 pos=(0, 0))
        root.add_widget(game_widget)
        return root

if __name__ == '__main__':
    CampApp().run()