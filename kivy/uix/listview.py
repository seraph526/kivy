'''
List View
===========

.. versionadded:: 1.4

The :class:`ListView` widget provides a scrollable/pannable viewport that is
clipped at the scrollview's bounding box, which contains a list of items.

'''

__all__ = ('ListView', )

from kivy.clock import Clock
from kivy.event import EventDispatcher
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.properties import ObjectProperty, DictProperty, \
                            NumericProperty
from kivy.lang import Builder
from math import ceil, floor
from kivy.uix.mixins.selection import SelectionSupport

Builder.load_string('''
<ListView>:
    container: container
    ScrollView:
        pos: root.pos
        on_scroll_y: root._scroll(args[1])
        do_scroll_x: False
        GridLayout:
            cols: 1
            id: container
            size_hint_y: None
''')


class Adapter(SelectionSupport, EventDispatcher):
    '''Adapter is a bridge between an AbstractView and the data.
    '''

    cls = ObjectProperty(None)

    template = ObjectProperty(None)

    converter = ObjectProperty(None)

    def __init__(self, **kwargs):
        self.register_event_type('on_select')
        if kwargs['selection_mode'] is not None:
            if kwargs['selection_mode'] in ['single', 'multiple', 'filter']:
                self.selection_mode = kwargs['selection_mode']
        super(Adapter, self).__init__(**kwargs)
        if self.cls is None and self.template is None:
            raise Exception('A cls or template must be defined')
        if self.cls is not None and self.template is not None:
            raise Exception('Cannot use cls and template at the same time')

    def get_count(self):
        raise NotImplementedError()

    def get_item(self, index):
        raise NotImplementedError()

    def get_view(self, index):
        item = self.get_item(index)
        if item is None:
            return None
        if self.converter:
            item = self.converter(item)
        if self.cls:
            print 'CREATE VIEW FOR', index
            item_instance = self.cls(
                selection_callback=self.select_object,
                **item)
            return item_instance
        return Builder.template(self.template, **item)

    # This is for the list adapter, if it wants to get selection events.
    def on_select(self, *args):
        pass

    # Things to think about:
    #
    # There are other possibilities:
    #
    #         Additional possibilities, to those stubbed out in
    #         methods below.
    #
    #             - a boolean for whether or not editing of items is allowed
    #             - a boolean for whether or not to destroy on removal (if
    #               applicable)
    #             - guards for adding, removing, sorting items
    #

    def add_item(self, item):
        pass

    def remove_item(self, item):
        pass

    def replace_item(self, item):
        pass

    # This method would have an associated sort_key property.
    def sorted_items(self):
        pass


class ListAdapter(Adapter):
    '''Adapter around a simple Python list
    '''

    def __init__(self, arranged_objects, **kwargs):
        super(ListAdapter, self).__init__(**kwargs)
        if type(arranged_objects) not in (tuple, list):
            raise Exception('ListAdapter: input must be a tuple or list')
        self.arranged_objects = arranged_objects

    def get_count(self):
        return len(self.arranged_objects)

    def get_item(self, index):
        if index < 0 or index >= len(self.arranged_objects):
            return None
        return self.arranged_objects[index]


class AbstractView(FloatLayout):
    '''View using an Adapter as a data provider
    '''

    adapter = ObjectProperty(None)

    items = DictProperty({})

    def set_item(self, index, item):
        pass

    def get_item(self, index):
        items = self.items
        if index in items:
            return items[index]
        item = self.adapter.get_view(index)
        if item:
            items[index] = item
        return item


class ListView(AbstractView):
    '''Implementation of an Abstract View as a vertical scrollable list.
    '''

    divider = ObjectProperty(None)

    divider_height = NumericProperty(2)

    container = ObjectProperty(None)

    row_height = NumericProperty(None)

    _index = NumericProperty(0)
    _sizes = DictProperty({})
    _count = NumericProperty(0)

    _wstart = NumericProperty(0)
    _wend = NumericProperty(None)

    def __init__(self, **kwargs):
        super(ListView, self).__init__(**kwargs)
        self._trigger_populate = Clock.create_trigger(self._spopulate, -1)
        self.bind(size=self._trigger_populate,
                pos=self._trigger_populate)
        self.populate()

    def _scroll(self, scroll_y):
        if self.row_height is None:
            return
        scroll_y = 1 - min(1, max(scroll_y, 0))
        container = self.container
        mstart = (container.height - self.height) * scroll_y
        mend = mstart + self.height

        # convert distance to index
        rh = self.row_height
        istart = int(ceil(mstart / rh))
        iend = int(floor(mend / rh))

        istart = max(0, istart - 1)
        iend = max(0, iend - 1)

        if istart < self._wstart:
            rstart = max(0, istart - 10)
            self.populate(rstart, iend)
            self._wstart = rstart
            self._wend = iend
        elif iend > self._wend:
            self.populate(istart, iend + 10)
            self._wstart = istart
            self._wend = iend + 10

    def _spopulate(self, *dt):
        self.populate()

    def populate(self, istart=None, iend=None):
        print 'populate', istart, iend
        container = self.container
        sizes = self._sizes
        rh = self.row_height

        # ensure we know what we want to show
        if istart is None:
            istart = self._wstart
            iend = self._wend

        # clear the view
        container.clear_widgets()

        # guess only ?
        if iend is not None:

            # fill with a "padding"
            fh = 0
            for x in xrange(istart):
                fh += sizes[x] if x in sizes else rh
            container.add_widget(Widget(size_hint_y=None, height=fh))

            # now fill with real item
            index = istart
            while index <= iend:
                item = self.get_item(index)
                index += 1
                if item is None:
                    continue
                sizes[index] = item.height
                container.add_widget(item)

        else:
            available_height = self.height
            real_height = 0
            index = self._index
            count = 0
            while available_height > 0:
                item = self.get_item(index)
                sizes[index] = item.height
                index += 1
                count += 1
                container.add_widget(item)
                available_height -= item.height
                real_height += item.height

            self._count = count

            # extrapolate the full size of the container from the size
            # of items
            if count:
                container.height = \
                    real_height / count * self.adapter.get_count()
                if self.row_height is None:
                    self.row_height = real_height / count
