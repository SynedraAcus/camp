import sys
import random


#  Little more than a placeholder. There is only movement, and it allows to use
#  numpad and nethack-like vim keys. WASD and arrows
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


class Controller(object):
    """
    Controller class. It should be attached to actor.
    All Controller subclasses should provide call_actor_method() method that will make actor perform the
    required action and return its result (normally a boolean value). Player-controlled subclasses
    should also provide take_keycode method that will take kivy keycode and make the next call to
    self.call_actor_method() perform appropriate action for that keycode.
    """
    def __init__(self):
        self.last_command = None
        self.actor = None

    def call_actor_method(self):
        """
        Call the actor method that corresponds to self.last_command and return its result
        :return: bool
        """
        raise NotImplementedError('Base Controller class does not actually call actor methods')



class PlayerController(Controller):
    """
    Controller subclass that allows passing keycode to the actor.
    It also parses the keys
    """
    def __init__(self, commands=command_dict):
        super(Controller, self).__init__()
        self.commands = {}
        self.load_commands(commands)

    def load_commands(self, d):
        """
        Load the command dictionary. It should be in a {'command': [button1, button2]} form.
        List of available commands is predefined
        :param commands:
        :return:
        """
        for command in d.items():
            self.commands.update({x: command[0] for x in command[1]})

    def take_keycode(self, keycode):
        """
        Take the keycodeis that will be processed during actor's next turn. Return True if the keycode is
        recognised, False otherwise.
        :param keycode: keycode
        :return: bool
        """
        try:
            self.last_command = self.commands[keycode[1]]
            return True
        except KeyError:
            return False

    def call_actor_method(self):
        if not self.actor:
                raise AttributeError('Controller cannot be used when not attached to actor')
        #  Methods to call for every action are defined here. Later I'll build some more complex system
        #  using getattr, loading commands, their methods and arguments from external source and so on
        #  Boilerplate will do for now
        if self.last_command == 'wait':
            r = self.actor.pause()
        #  Cardinal movement
        elif self.last_command == 'walk_8':
            r = self.actor.move(location=(self.actor.location[0], self.actor.location[1]+1))
        elif self.last_command == 'walk_6':
            r = self.actor.move(location=(self.actor.location[0]+1, self.actor.location[1]))
        elif self.last_command == 'walk_2':
            r = self.actor.move(location=(self.actor.location[0], self.actor.location[1]-1))
        elif self.last_command == 'walk_4':
            r = self.actor.move(location=(self.actor.location[0]-1, self.actor.location[1]))
        #  Diagonal movement
        elif self.last_command == 'walk_7':
            r = self.actor.move(location=(self.actor.location[0]-1, self.actor.location[1]+1))
        elif self.last_command == 'walk_9':
            r = self.actor.move(location=(self.actor.location[0]+1, self.actor.location[1]+1))
        elif self.last_command == 'walk_1':
            r = self.actor.move(location=(self.actor.location[0]-1, self.actor.location[1]-1))
        elif self.last_command == 'walk_3':
            r = self.actor.move(location=(self.actor.location[0]+1, self.actor.location[1]-1))
        self.last_command = None
        return r


class AIController(Controller):
    """
    Controller subclass that just orders walk_9 at every turn
    """
    def __init__(self):
        super(AIController, self).__init__()

    def call_actor_method(self):
        """
        The primitive AI routine. If there are neighbours, attack a random one, otherwise walk_9
        :return:
        """
        neighbours = self.actor.map.get_neighbours(layer='actors', location=self.actor.location)
        if len(neighbours) > 0:
            victim = random.choice(neighbours)
            return self.actor.move(victim.location)
        else:
            return self.actor.move((self.actor.location[0]+1, self.actor.location[1]+1))

    def choose_actor_action(self):
        self.last_command = 'walk_9'