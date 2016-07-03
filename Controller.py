import sys
import random



class Command(object):
    """
    The command for PlayerController. This is purely a data class without any logic. Like Effect class,
    it contains only two attributes: command type and command value.
    command_type should be one of the string values defined in Command.acceptable_commands
    command_value should be an iterable or None
    """
    acceptable_commands = ('walk', 'use_item', 'wait', 'grab', 'drop_item')
    def __init__(self, command_type=None, command_value=None):
        assert command_type in self.acceptable_commands
        self.command_type = command_type
        self.command_value = command_value


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
        if not self.actor:
            raise AttributeError('Controller cannot be used when not attached to actor')
        if self.last_command.command_type == 'wait':
            r = self.actor.pause()
        #  Cardinal movement
        elif self.last_command.command_type == 'walk':
            r = self.actor.move(location=(self.actor.location[0]+self.last_command.command_value[0],
                                          self.actor.location[1]+self.last_command.command_value[1]))
        #  Item usage
        elif self.last_command.command_type == 'use_item':
            r = self.actor.use_item(self.last_command.command_value[0])
        #  Grabbing & Dropping
        elif self.last_command.command_type == 'grab':
            r = self.actor.grab()
        elif self.last_command.command_type == 'drop_item':
            r = self.actor.drop_item(self.last_command.command_value[0])
        self.last_command = None
        return r



class PlayerController(Controller):
    """
    Controller subclass that allows processing Commands.
    It also parses the keys
    """
    def __init__(self):
        super(Controller, self).__init__()
        self.commands = {}
        # self.load_commands(commands)
    #
    # def load_commands(self, d):
    #     """
    #     Load the command dictionary. It should be in a {'command': [button1, button2]} form.
    #     List of available commands is predefined
    #     :param commands:
    #     :return:
    #     """
    #     for command in d.items():
    #         self.commands.update({x: command[0] for x in command[1]})

    def take_keycode(self, keycode):
        """
        Take the keycodeis that will be processed during actor's next turn. Return True if the keycode is
        recognised, False otherwise.
        :param keycode: keycode
        :return: bool
        """
        # try:
        #     self.last_command = self.commands[keycode[1]]
        #     return True
        # except KeyError:
        #     return False
        self.accept_command(self.commands[keycode[1]])
        return True

    accepted_command_types = ('walk', 'use_item', 'wait', 'grab', 'drop_item')

    def accept_command(self, command):
        if command.command_type not in self.accepted_command_types:
            raise ValueError('Invalid command passed to Controller instance')
        else:
            self.last_command = command
            return True

    # def call_actor_method(self):
    #     if not self.actor:
    #         raise AttributeError('Controller cannot be used when not attached to actor')
    #     if self.last_command.command_type == 'wait':
    #         r = self.actor.pause()
    #     #  Cardinal movement
    #     elif self.last_command.command_type == 'walk':
    #         r = self.actor.move(location=(self.actor.location[0]+self.last_command.command_value[0],
    #                                       self.actor.location[1]+self.last_command.command_value[1]))
    #     #  Item usage
    #     elif self.last_command.command_type == 'use_item':
    #         r = self.actor.use_item(self.last_command.command_value[0])
    #     #  Grabbing & Dropping
    #     elif self.last_command.command_type == 'grab':
    #         r = self.actor.grab()
    #     elif self.last_command.command_type == 'drop_item':
    #         r = self.actor.drop_item(self.last_command.command_value[0])
    #     self.last_command = None
    #     return r


class AIController(Controller):
    """
    Controller subclass that just orders walk_9 at every turn
    """
    def __init__(self):
        super(AIController, self).__init__()

    def _should_attack(self, other):
        """
        Decide whether actor should attack other in melee
        :param other:
        :return:
        """
        if other.fighter:
            print('Is fighter')
            if self.actor.faction.is_enemy(other.faction):
                print ('Should be attacked')
                return True
        return False

    def choose_actor_action(self):
        #  Fight combat-capable neighbours from enemy factions, if any
        neighbours = self.actor.map.get_neighbours(layer='actors', location=self.actor.location)
        neighbours = list(filter(self._should_attack, neighbours))
        if len(neighbours) > 0:
            print('Entered attack lines')
            victim = random.choice(neighbours)
            self.last_command = Command(command_type='walk',
                                        command_value=(victim.location[0]-self.actor.location[0],
                                                       victim.location[1]-self.actor.location[1]))
        else:
            print('Entered peaceful lines')
            self.last_command = Command(command_type='walk',
                                        command_value=(1, 1))