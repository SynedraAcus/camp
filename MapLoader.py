"""
The classes responsible for loading levels from files. This file is supposed to be imported by Factories.py and
 nobody else
"""

class MapLoader():
    """
    The map file interface. It takes a filehandle and returns a complete map. Everything it needs to do so is not
    the caller's problem.
    """
    def __init__(self):
        pass

    def read_map_file(self):
        """
        Read a file that contains a single map
        :return:
        """
        pass