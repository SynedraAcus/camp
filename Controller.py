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
        Decide whether Actor should attack other Actor in melee
        :param other:
        :return:
        """
        if other.fighter:
            if self.actor.faction.is_enemy(other.faction):
                return True
        return False

    def _should_walk(self, location):
        """
        Decide whether actor should walk into a tile
        Only the coordinates for a tile are supplied
        :param location: tuple
        :return:
        """
        #  Check if there is a non-enemy fighter on the tile that Actor wants to enter
        for item in self.actor.map.get_column(location):
            try:
                if item.fighter and not self._should_attack(item):
                    return False
            except AttributeError:
                #  There may not even be a fighter attribute
                pass
        return True

    def get_visible_items(self, layer='actors', filter_function=None):
        """
        Get all the visible items on a given layer.
        Return an iterable of all items, filtered if filter argument is supplied.
        If filter is supplied, it should be a one-argument function that accepts MapItem (or a subclass)
        as the only argument. It should return True for MapItems of interest, exactly like a filter()
        1st argument
        :param layer:
        :param filter:
        :return:
        """
        #  For now no LoS is calculated and every NPC can see the entire map
        l = []
        for x in range(self.actor.map.size[0]):
            for y in range(self.actor.map.size[1]):
                i = self.actor.map.get_item(layer=layer, location=(x, y))
                if i:
                    l.append(i)
        l = tuple(filter(filter_function, l))
        return l


    def choose_actor_action(self):
        #  Fight combat-capable neighbours from enemy factions, if any
        neighbours = self.actor.map.get_neighbours(layer='actors', location=self.actor.location)
        neighbours = list(filter(self._should_attack, neighbours))
        if len(neighbours) > 0:
            victim = random.choice(neighbours)
            self.last_command = Command(command_type='walk',
                                        command_value=(victim.location[0]-self.actor.location[0],
                                                       victim.location[1]-self.actor.location[1]))
        else:
            if self._should_walk((self.actor.location[0]+1, self.actor.location[1]+1)):
                self.last_command = Command(command_type='walk',
                                            command_value=(1, 1))
            else:
                self.last_command = Command(command_type='wait')