#! /usr/bin/env python3
#  Kivy imports
import kivy
kivy.require('1.9.0')
from kivy.app import App
from kivy.config import Config
from kivy.graphics.context_instructions import Rotate, Translate
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.core.audio import SoundLoader

#  My own stuff
from Factories import TileWidgetFactory, MapLoader
from Controller import Command
from GameEvent import EventQueue
from Listeners import Listener, DeathListener, BorderWalkListener

#  Others
from math import atan2, degrees

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


class GameManager():
    """
    A singleton game manager. It holds data about current map, GameEvent queue and so on.
    Basically anything that is neither interface nor is limited to a single map/actor belongs here
    """
    def __init__(self, map_file='test_level.lvl'):
        self.queue = EventQueue()
        self.map_loader = MapLoader()
        self.map_loader.read_map_file(map_file)
        self.map = None
        self.game_widget = None
        #  Log list. Initial values allow not to have empty log at the startup
        self.game_log = ['Игра начинается', 'Если вы видите этот текст, то кириллический лог работает',
                         'All the text below will be in English, so I guess Latin log works as well']

    def load_map(self, map_id='start'):
        """
        Load a new map with a given ID.
        Doesn't do anything to widgets: just loads the map and connects the queue. The first map loaded is
        drawn by GameWidget's __init__(), for others you should call self.switch_map() manually
        :param map_id: str
        :return: Map
        """
        self.map = self.map_loader.get_map_by_id(map_id)
        self.map.register_manager(self)
        return self.map

    def switch_map(self, map_id='start'):
        """
        Switch to a new map.
        Assumes the map is available from self.map_loader. The queue is cleaned up because otherwise
        some animations on non-displayed items are run after switch.
        :param map_id:
        :return:
        """
        self.queue.clear()
        self.load_map(map_id)
        self.game_widget.rebuild_widgets()

    def process_events(self):
        """
        Process all events in a queue
        :return:
        """
        self.queue.pass_all_events()

    def register_listener(self, listener):
        """
        Add a queue listener to both queue and self.
        Listeners registered here get their game_manager attribute set to self. It can allow them to interact
        with the game, ordering GameManager to change levels, finish the game and so on.
        Thus, it's advised to use this method only for listeners that need to do so; achievement trackers,
        interface listeners and whatever else *views* the game should be registered to queue directly.
        :param listener:
        :return:
        """
        self.queue.register_listener(listener)
        listener.game_manager = self



class GameWidget(RelativeLayout):
    """
    Main game widget. Includes map, as well as various other widgets, as children.
    The game state is tracked by this widget's self.state
    """
    def __init__(self, game_manager=None, **kwargs):
        super(GameWidget, self).__init__(**kwargs)
        self.game_manager = game_manager
        self.game_manager.game_widget = self
        self.rebuild_widgets()
        #  Sound object
        self.boombox = {'moved': SoundLoader.load('dshoof.wav'),
                        'attacked': SoundLoader.load('dspunch.wav'),
                        'exploded': SoundLoader.load('dsbarexp.wav')}
        #  Sound in kivy seems to be loaded lazily. Files are not actually read until they are necessary,
        #  which leads to lags for up to half a second when a sound is used for the first time. The following
        #  two lines are forcing them to be loaded right now.
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
                             #  PC stats view
                             'c',
                             #  Used for inventory & spell systems
                             '0', '1', '2', '3', '4', '5',
                             '6', '7', '8', '9',
                             #  Inventory management
                             'g', ',', 'd', 'i',
                             #  Targeted effects
                             'z', 'x', 'f',
                             #  Others
                             'escape', 'enter', 'numpadenter']
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
        #  Stuff for various game states
        self.state_widget = None
        self.target_coordinates = (None, None)

    def rebuild_widgets(self):
        """
        Rebuild the widgets according to map in self.game_manager.
        This method DOESN'T resize the window if the map size changes.
        :return:
        """
        #  Initializing widgets
        self.map_widget = RLMapWidget(map=self.game_manager.map,
                                      size=(self.game_manager.map.size[0]*32,
                                            self.game_manager.map.size[1]*32),
                                      size_hint=(None, None),
                                      pos=(0, 100))
        self.log_widget = LogWindow(id='log_window',
                                    text='\n'.join(self.game_manager.game_log[-3:]),
                                    size=(self.map_widget.width, 100),
                                    size_hint=(None, None),
                                    pos=(0, 0),
                                    text_size=(self.map_widget.width, 100),
                                    padding=(20, 5),
                                    font_size=10,
                                    valign='top',
                                    line_height=1)
        self.height = self.map_widget.height+self.log_widget.height
        self.width = self.map_widget.width
        self.add_widget(self.map_widget)
        self.add_widget(self.log_widget)
        #  Registering MapWidget to receive events from GameManager
        self.game_manager.queue.register_listener(self.map_widget)
        self.game_manager.register_listener(self.log_widget)

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
                    #  If the key is a 'map-controlling' one, ie uses a turn without calling further windows
                    command = self.key_parser.key_to_command(keycode)
                    self.game_manager.map.process_turn(command=command)
                elif keycode[1] == 'escape':
                    App.get_running_app().stop()
                #  The following checks set various game states but don't, by themselves, produce commands
                elif keycode[1] in 'c':
                    #  Displaying player stats window
                    self.game_state = 'stat_window'
                    self.state_widget = LogWindow(pos=(200, 200),
                                                  size=(200, 200),
                                                  size_hint=(None, None),
                                                  text=self.map_widget.map.actors[0].descriptor.get_description(
                                                     combat=True))
                    self.add_widget(self.state_widget)
                elif keycode[1] in 'i':
                    self.game_state = 'inv_window'
                    self.state_widget = LogWindow(pos=(200, 200),
                                                  size=(200, 200),
                                                  size_hint=(None, None),
                                                  text=self.map_widget.map.actors[0].inventory.get_string())
                    self.add_widget(self.state_widget)
                elif keycode[1] in 'd':
                    self.game_state = 'drop_window'
                    self.state_widget = LogWindow(pos=(200, 200),
                                                  size=(200, 200),
                                                  size_hint=(None, None),
                                                  text=self.map_widget.map.actors[0].inventory.get_string())
                    self.add_widget(self.state_widget)
                elif keycode[1] in 'z':
                    self.game_state = 'jump_targeting'
                    self.target_coordinates = self.map_widget.map.actors[0].location
                    self.state_widget = Image(source='JumpTarget.png',
                                              pos=self.map_widget.get_screen_pos(self.target_coordinates,
                                                                                  parent=True),
                                              size=(32, 32),
                                              size_hint=(None, None))
                    self.add_widget(self.state_widget)
                elif keycode[1] in 'x':
                    self.game_state = 'examine_targeting'
                    self.target_coordinates = self.map_widget.map.actors[0].location
                    self.state_widget = Image(source='ExamineTarget.png',
                                              pos=self.map_widget.get_screen_pos(self.target_coordinates,
                                                                                 parent=True),
                                              size=(32, 32),
                                              size_hint=(None, None))
                    self.add_widget(self.state_widget)
                elif keycode[1] in 'f':
                    self.game_state = 'fire_targeting'
                    self.target_coordinates = self.map_widget.map.actors[0].location
                    self.state_widget = Image(source='FireTarget.png',
                                              pos=self.map_widget.get_screen_pos(self.target_coordinates,
                                                                                   parent=True),
                                              size=(32, 32),
                                              size_hint=(None, None))
                    self.add_widget(self.state_widget)
            else:
                #  Process various non-'playing' game states, hopefully making a command
                if ('window' in self.game_state or 'targeting' in self.game_state) \
                        and keycode[1] in ('i', 'c', 'g', 'd', 'escape'):
                    #  Escape and window-calling buttons switch state to 'playing', doing nothing else
                    self.remove_widget(self.state_widget)
                    self.game_state = 'playing'
                elif self.game_state == 'inv_window':
                    #  Try to use keycode as inventory command
                    try:
                        n = self.key_parser.key_to_number(keycode)
                        command = Command(command_type='use_item', command_value=(n, ))
                        self.remove_widget(self.state_widget)
                        self.game_state = 'playing'
                        self.game_manager.map.process_turn(command=command)
                    except ValueError:
                        #  This ValueError is expected to be raised by key_to_number if the keycode
                        #  is not numeric
                        pass
                elif self.game_state == 'drop_window':
                    #  Try to use keycode as drop command
                    try:
                        n = self.key_parser.key_to_number(keycode)
                        command = Command(command_type='drop_item', command_value=(n, ))
                        #  Remove inventory widget upon using item
                        self.remove_widget(self.state_widget)
                        self.game_state = 'playing'
                        self.game_manager.map.process_turn(command=command)
                    except ValueError:
                        pass
                elif 'targeting' in self.game_state:
                    if self.game_state == 'jump_targeting' and keycode[1] in ('z', 'enter', 'numpadenter'):
                        #  Finish jump targeting
                        delta = (self.target_coordinates[0]-self.map_widget.map.actors[0].location[0],
                                 self.target_coordinates[1]-self.map_widget.map.actors[0].location[1])
                        command = Command(command_type='jump', command_value=delta)
                        self.game_state = 'playing'
                        self.remove_widget(self.state_widget)
                        self.game_manager.map.process_turn(command=command)
                    elif self.game_state == 'examine_targeting' and keycode[1] in ('x', 'enter', 'numpadenter'):
                        #  Examine whatever is under cursor
                        self.game_state = 'examine_window'
                        self.remove_widget(self.state_widget)
                        try:
                            t = self.map_widget.map.get_top_item(location=self.target_coordinates).descriptor.get_description(
                                combat=True)
                        except AttributeError:
                            t = 'Nothing of note'
                        self.state_widget = LogWindow(pos=(200, 200),
                                                      size=(200, 200),
                                                      size_hint=(None, None),
                                                      text=t)
                        self.add_widget(self.state_widget)
                    elif self.game_state == 'fire_targeting' and keycode[1] in ('f', 'enter', 'numpadenter'):
                        #  Shooting to the cursor
                        command = Command(command_type='shoot',
                                          command_value=self.target_coordinates)
                        self.game_state = 'playing'
                        self.remove_widget(self.state_widget)

                        self.game_manager.map.process_turn(command)
                    elif keycode[1] in self.key_parser.command_types.keys() and \
                                    self.key_parser.command_types[keycode[1]] == 'walk':
                        #  Move the targeting widget
                        delta = self.key_parser.command_values[keycode[1]]
                        self.target_coordinates = [self.target_coordinates[0]+delta[0],
                                                   self.target_coordinates[1]+delta[1]]
                        self.state_widget.pos = self.map_widget.get_screen_pos(self.target_coordinates,
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
        self.log_widget.canvas.ask_update()

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
                    tile_widget = parent.tile_factory.create_widget(item)
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

class RLMapWidget(RelativeLayout, Listener):
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
        #  Queue of GameEvents to be animated
        self.animation_queue = []
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
##########################################################
    def process_game_event(self, event):
        """
        Process a GameEvent passed by queue
        :param event: GameEvent
        :return:
        """
        if event.event_type == 'queue_exhausted':
            #  Shoot animations only after the entire event batch for the turn has arrived
            #  Better to avoid multiple methods messing with self.animation_queue simultaneously
            self.animate_game_event()
        #  Ignore log-related events
        elif not event.event_type == 'log_updated':
            self.animation_queue.append(event)

    def animate_game_event(self, widget=None, anim_duration=0.3):
        """
        Process a single event from self.animation_queue
        Read the event and perform the correct actions on widgets (such as update text of log window,
        create and launch animation, maybe make some sound). The event is removed from self.map.game_events.
        After the actions required are performed, the method calls itself again, either recursively, or, in
        case of animations, via Animation's on_complete argument. The recursion is broken when event queue is
        empty.
        :return:
        """
        if widget and widget.parent and widget.height < 1:
            #  If the widget was given zero size, this means it should be removed
            #  This entire affair is kinda inefficient and should be rebuilt later
            widget.parent.remove_widget(widget)
        if not self.animation_queue == []:
            event = self.animation_queue.pop(0)
            if event.event_type == 'moved':
                final = self.get_screen_pos(event.actor.location)
                a = Animation(x=final[0], y=final[1], duration=anim_duration)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.animate_game_event(widget=y))
                a.start(event.actor.widget)
            elif event.event_type == 'attacked':
                current = self.get_screen_pos(event.actor.location)
                target = self.get_screen_pos(event.location)
                a = Animation(x=current[0]+int((target[0]-current[0])/2),
                              y=current[1]+int((target[1]-current[1])/2),
                              duration=anim_duration/2)
                a += Animation(x=current[0], y=current[1], duration=anim_duration/2)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.animate_game_event(widget=y))
                a.start(event.actor.widget)
                self.parent.boombox['attacked'].play()
            elif event.event_type == 'was_destroyed':
                if not event.actor.widget:
                    #  If actor is None, that means it was destroyed right after spawning, not getting a
                    #  widget. Similar case is covered under 'dropped', see there for example. The check is
                    #  different here, because in 'dropped' item is taken from map, where it's None by the time
                    #  this method runs. Here, on the other hand, Item object exists (in GameEvent), but has
                    #  no widget (and is not placed on map, but that's irrelevant).
                    self.animate_game_event()
                    return
                a = Animation(size=(0, 0), duration=anim_duration)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.animate_game_event(widget=y))
                a.start(event.actor.widget)
            elif event.event_type == 'picked_up':
                #  It's assumed that newly added item will be the last in player inventory
                self.layer_widgets['items'].remove_widget(self.map.actors[0].inventory[-1].widget)
                self.animate_game_event()
            elif event.event_type == 'dropped':
                item = self.map.get_item(location=event.location, layer='items')
                if not item:
                    #  Item could've been destroyed right after being drop, ie it didn't get a widget. Skip.
                    #  It's rather likely if someone was killed by landmine, dropped an item and had this item
                    #  destroyed in the same explosion
                    self.animate_game_event()
                    return
                if not item.widget:
                    self.tile_factory.create_widget(item)
                    item.widget.pos = self.get_screen_pos(event.location)
                self.layer_widgets['items'].add_widget(item.widget)
                self.animate_game_event()
            elif event.event_type == 'actor_spawned':
                a = event.actor
                if not a.widget:
                    self.tile_factory.create_widget(a)
                    a.widget.pos = self.get_screen_pos(event.location)
                self.layer_widgets['actors'].add_widget(a.widget)
                self.animate_game_event()
            elif event.event_type == 'construction_spawned':
                a = event.actor
                if not a.widget:
                    self.tile_factory.create_widget(a)
                    a.widget.pos = self.get_screen_pos(event.location)
                self.layer_widgets['constructions'].add_widget(a.widget)
                self.animate_game_event()
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
                       on_complete=lambda x, y: self.animate_game_event(widget=y))
                self.add_widget(self.overlay_widget)
                self.parent.boombox['exploded'].play()
                a.start(self.overlay_widget)
            elif event.event_type == 'shot':
                self.overlay_widget = RelativeLayout(pos=self.get_screen_pos(event.actor.location),
                                                     size=(64, 64),
                                                     size_hint=(None, None))
                i = Image(source='Rocket.png',
                          size=(32, 32),
                          size_hint=(None, None))
                self.overlay_widget.add_widget(i)
                self.overlay_widget.canvas.before.add(Translate(x=32, y=32))
                a = degrees(atan2(event.actor.location[1]-event.location[1],
                                  event.actor.location[0]-event.location[0]))
                # print(a)
                if a > 180:
                    self.overlay_widget.y += 32
                self.overlay_widget.canvas.before.add(Rotate(angle=a+90, axis=(0, 0, 1)))
                a = Animation(pos=self.get_screen_pos(event.location), duration=anim_duration)
                a += Animation(size=(0,0), duration=0)
                a.bind(on_start=lambda x, y: self.remember_anim(),
                       on_complete=lambda x, y: self.animate_game_event(widget=y))
                self.add_widget(self.overlay_widget)
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


class LogWindow(Label, Listener):
    """ Text widget that shows the last 3 items from game_log
    """
    def __init__(self, *args, **kwargs):
        super(LogWindow, self).__init__(*args, **kwargs)
        self.text_size = self.size
        self.halign = 'left'
        self.valign = 'top'
        with self.canvas.before:
            Color(1, 0, 0)
            Rectangle(size=self.size, pos=self.pos)

    def process_game_event(self, event):
        """
        Update text according to the event
        :return:
        """
        if event.event_type == 'log_updated':
            if len(self.game_manager.game_log) > 6:
                self.text = '\n'.join(self.game_manager.game_log[-6:])
            else:
                self.text = '\n'.join(self.game_manager.game_log)
            self.canvas.ask_update()



class CampApp(App):
    """
    Main app class.
    """
    def __init__(self):
        super(CampApp, self).__init__()
        self.game_manager = None
        self.game_widget = None

    def build(self):
        root = BoxLayout(orientation='vertical')
        self.game_manager = GameManager(map_file='test_level.lvl')
        self.game_manager.load_map('start')
        self.game_widget = GameWidget(game_manager=self.game_manager,
                                      size=Window.size,
                                      size_hint=(None, None),
                                      pos=(0, 0))
        self.game_manager.register_listener(DeathListener())
        self.game_manager.register_listener(BorderWalkListener())
        Window.size = self.game_widget.size
        root.add_widget(self.game_widget)
        return root

if __name__ == '__main__':
    Config.set('kivy', 'exit_on_escape', 0)
    CampApp().run()