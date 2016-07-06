"""
Map item classes. This module contains the base MapItem class and all of its children
that are not Actors (those are in Actor.py).
"""

class MapItem(object):
    """
    Base class from which all items that can be placed on map should inherit
    """
    def __init__(self, passable=True, image_source=None):
        self.passable = passable
        self.widget = None

    def collide(self, other):
        """ Collisions are expected to be overridden if they are to actually do something.
        This method returns False indicating that nothing happened."""
        return False


class GroundTile(MapItem):
    def __init__(self, passable=True, image_source='Tmp_frame.png', **kwargs):
        super(GroundTile, self).__init__(**kwargs)
        self.passable=passable
        self.image_source = image_source
        #  Widget should be defined when a tile is added to the RLMapWidget using TileWidgetFactory
        self.widget = None