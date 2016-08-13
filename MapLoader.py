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
        #  A dict of tag-to-function mappings. Values should be callables that accept string a return an object of
        #  required type
        self.tag_converters = {'height': int,
                               'width': int,
                               'aesthetic': str}

    def parse_tag_line(self, line):
        """
        Parse a tag line
        Convert the value to the required type (as per tag_types) and return (key, value) pair
        :param line:
        :return:
        """
        line = line.lstrip('/')
        a = line.split()
        if len(a) == 2:
            try:
                r = a[0], self.tag_converters[a[0]](a[1])
            except KeyError:
                raise ValueError('Unknown tag {0} in the map file'.format(a[0]))
        else:
            raise ValueError('Incorrect tag line "{0}"'.format(line))
        return r

    def read_map_file(self, handle):
        """
        Read a file that contains a single map
        :param handle: filehandle to a *.lvl file
        :return:
        """
        tags = {}
        map_lines = []
        reading_map = False
        for line in handle:
            if line[0]=='/':
                if reading_map:
                    #  Only read tags *before* the map
                    break
                l = self.parse_tag_line(line)
                tags.update({l[0]: l[1]})
            else:
                map_lines.append(line)
                reading_map = True
        # print(tags)
        # print('\n'.join(map_lines))