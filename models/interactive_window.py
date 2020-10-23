'''
Matplotlib enhanced with interactive plotting using ipywidgets.

 - The IPWInteract class can generate a simple interface to a model that
   inherits from InteractiveModel. The parameters specified in `param_names`
   are included in the interactive interface.

   Further, the order of param_names can be used to transform the traits
   of the model into a tuple that calls that can be called the lambdified
   functions. This feature is useful for direct integration of function
   derived symbolically using sympy.

   @todo: define param_names as
   - ipw_interact = ['a', 'b'] as a specifier which values are to be included in the interaction
   - ipw_observe = ['d', 'e' ]

   @todo: use ipwidget metadata attribute to overload the ipw_map
'''

import ipywidgets as ipw
import traits.api as tr
import matplotlib.pylab as plt

ipw_map = \
    {
        tr.Float: ipw.FloatSlider,
        tr.Int: ipw.IntSlider,
        tr.Bool: ipw.ToggleButton
    }


class Item(tr.HasTraits):
    """Item of interaction with a model
    """
    name = tr.Str
    latex = tr.Str
    minmax = tr.Tuple

    editor = None
    '''Overload the editor defined in the trait type'''

    latex_str = tr.Property

    def _get_latex_str(self):
        if self.latex:
            return self.latex
        else:
            return self.name

    def __init__(self, name, **traits):
        self.name = name
        tr.HasTraits.__init__(self, **traits)

    def get_editor(self, value, trait, model):
        if self.editor:
            editor = self.editor
        else:
            # create a new edior using the factory provided by the trait type
            if trait.trait_type.editor_factory == None:
                raise TypeError('no editor for %s with type %s' % (self.name,trait.trait_type) )
            editor = trait.trait_type.editor_factory()
        # use the editor supplied in the item defintion and set its attributes
        editor.label = self.latex_str
        editor.value = value
        editor.trait = trait
        editor.model = model
        return editor


class View(tr.HasTraits):
    """Container of IPWItems
    """
    content = tr.List(Item)
    item_names = tr.List(tr.Str)

    # -------------------------------------------------------------------------
    #  Initializes the object:
    # -------------------------------------------------------------------------

    def __init__(self, *values, **traits):
        """ Initializes the object.
        """
        tr.HasTraits.__init__(self, **traits)
        for item in values:
            self.content.append(item)
            self.item_names.append(item.name)


class IInteractiveModel(tr.Interface):
    """Interface of interactive models"""


@tr.provides(IInteractiveModel)
class InteractiveModel(tr.HasTraits):
    """Base class for interactive models
    """

    name = tr.Str("<unnamed>")

    def subplots(self, fig):
        return fig.subplots(1, 1)

    def plot(self, axes):
        '''Alias to update plot - to be overloaded by subclasses'''
        self.update_plot(axes)

    def update_plot(self, axes):
        raise NotImplementedError()

    def interact(self):
        return InteractiveWindow(self).interact()


class InteractiveWindow(tr.HasTraits):
    '''Container class synchronizing the interaction elements with plotting area.
    It is equivalent to the traitsui.View class
    '''
    models = tr.List(InteractiveModel)

    ipw_model_tabs = tr.List

    figsize = tr.Tuple(8, 3)

    def __init__(self, models, **kw):
        super(InteractiveWindow, self).__init__(**kw)
        if not (type(models) in [list, tuple]):
            models = [models]
        self.models = models
        self.ipw_model_tabs = [
            ModelTab(model=model, interactor=self, index=i)
            for i, model in enumerate(models)
        ]
        self.output = ipw.Output()
        with self.output:
            f = plt.figure(figsize=self.figsize, constrained_layout=True)
        f.canvas.toolbar_position = 'top'
        f.canvas.header_visible = False
        self.fig = f
        self.axes = self.models[0].subplots(self.fig)

    def __del__(self):
        plt.close(self.fig)

    def interact(self):
        tab = self.widget_layout()
        vb = ipw.VBox([self.output, tab])
        display(vb)

    def widget_layout(self):
        self.tab = ipw.Tab()
        keyval = [(elem.model.name, elem) for elem in self.ipw_model_tabs]
        self.tab.children = tuple(value.widget_layout() for _, value in keyval)
        [self.tab.set_title(i, key) for i, (key, val) in enumerate(keyval)]
        self.tab.observe(self.change_tab, 'selected_index')
        self.change_tab()
        return self.tab

    def change_tab(self, change=None):
        index = self.tab.selected_index
        self.fig.clf()
        self.axes = self.ipw_model_tabs[index].subplots(self.fig)
        self.update_plot(index)

    def update_plot(self, index):
        '''update the visualization with updated models'''
        _axes = self.axes
        if not hasattr(_axes, '__iter__'):
            _axes = [_axes]
        for ax in _axes:
            ax.clear()
        self.ipw_model_tabs[index].update_plot(self.axes)
        if len(self.tab.children) > index:
            self.tab.selected_index = index
        self.fig.canvas.draw()


from traits.trait_base import is_none


class ModelTab(tr.HasTraits):
    '''Base class for tabs within an interaction window.'''

    index = tr.Int

    model = tr.Instance(IInteractiveModel)

    interactor = tr.WeakRef

    def set_interactor(self, interactor):
        self.interactor = interactor

    n_steps = tr.Int(20)

    # @todo: an alternative implementation - analogy to traitsui.View
    def get_editors2(self):
        ipw_view = self.model.ipw_view
        item_names = ipw_view.item_names
        minmax_ = [ipw_item.minmax for ipw_item in ipw_view.content]
        latex_ = [ipw_item.latex_str for ipw_item in ipw_view.content]
        traits = self.model.traits(transient=is_none)
        values = self.model.trait_get(transient=is_none)
        traits_ = [traits[name] for name in item_names]
        val_ = [values[name] for name in item_names]
        return {name: ipw_map[trait_.trait_type.__class__](
            value=val, min=minmax[0], max=minmax[1],
            step=(minmax[1] - minmax[0]) / self.n_steps,
            continuous_update=False,
            description=r'\(%s\)' % latex)
            for (name, trait_, val, latex, minmax) in
            zip(item_names, traits_, val_, latex_, minmax_)
        }

    # @todo: an alternative implementation - analogy to traitsui.View
    def get_editors(self):
        ipw_view = self.model.ipw_view
        item_names = ipw_view.item_names
        items = ipw_view.content
        traits = self.model.traits(transient=is_none)
        traits = self.model.traits(transient=is_none)
        values = self.model.trait_get(transient=is_none)
        traits_ = [traits[name] for name in item_names]
        values_ = [values[name] for name in item_names]
        editors = {
            item.name: item.get_editor(value_, trait_, self.model)
            for (item, trait_, value_) in
            zip(items, traits_, values_)
        }
        return editors

    def ipw_editor_changed(self, change):
        name = change.owner.name
        val = change.new
        keyval = {name: val}
        self.model.trait_set(**keyval)
        self.interactor.update_plot(self.index)

    def widget_layout(self):
        editors = self.get_editors()
        ipw_editors = {}
        for name, editor in editors.items():
            ipw_editor = editor.render()
            ipw_editor.name = name
            ipw_editor.observe(self.ipw_editor_changed, 'value')
            ipw_editors[name] = ipw_editor
        # Originally, the interactive_ouput widget was used
        # here. But in this way, the update method was called
        # earlier than the tab change observer of the interactor
        # This caused problems if axes object did not correspond
        # to the model's update_plot method. Therefore,
        # slider observer is now used , augmented with the trait name.
        # out = ipw.interactive_output(self.update, sliders);
        layout = ipw.Layout(grid_template_columns='1fr 1fr')
        ipw_view = self.model.ipw_view
        item_names = ipw_view.item_names
        item_editors_list = [ipw_editors[name] for name in item_names]
        grid = ipw.GridBox(item_editors_list, layout=layout)
        return grid

    def subplots(self, fig):
        return self.model.subplots(fig)

    def update_plot(self, axes):
        self.model.update_plot(axes)
