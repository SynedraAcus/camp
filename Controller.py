from copy import copy

class Controller(object):
    """
    Controller class. It should be attached to actor; when order is passed to the controller,
    it will take a keycode and run the relevant actor's procedure when requested
    """
    def __init__(self):
        self.commands = {}
        self.last_command = None
        self.actor = None

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
        Take the keycode that will be processed during actor's next turn. Return True if the keycode is
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
        """
        Call the actor method that corresponds to self.last_command and return its result
        :return:
        """
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


#  Little more than a placeholder, again. There is only movement, and it allows to use
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

def create_prototype_controller():
    c = Controller()
    c.load_commands(command_dict)
    return c