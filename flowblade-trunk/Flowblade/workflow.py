"""
    Flowblade Movie Editor is a nonlinear video editor.
    Copyright 2012 Janne Liljeblad.

    This file is part of Flowblade Movie Editor <http://code.google.com/p/flowblade>.

    Flowblade Movie Editor is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Flowblade Movie Editor is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Flowblade Movie Editor.  If not, see <http://www.gnu.org/licenses/>.
"""

"""
Modeule handles displaying tool meni, tool keyboard shortuts and workflow configuration activating and moving tools,
and setting relevant timeline behaviours.

"""

import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from gi.repository import Gdk

import appconsts
import dialogs
import dialogutils
import edit
import editorpersistance
import editorstate
from editorstate import PROJECT
import gui
import guiutils
import modesetting
import respaths
import updater

# Timeline tools data
_TOOLS_DATA = None
_TOOL_TIPS = None

_tools_menu = Gtk.Menu()
_workflow_menu = Gtk.Menu()

def init_data():
    global _TOOLS_DATA, _TOOL_TIPS
    _TOOLS_DATA = { appconsts.TLINE_TOOL_INSERT:        (_("Insert"), "insertmove_cursor.png"),
                    appconsts.TLINE_TOOL_OVERWRITE:     (_("Move"), "overwrite_cursor.png"),
                    appconsts.TLINE_TOOL_TRIM:          (_("Trim"), "oneroll_cursor.png"),
                    appconsts.TLINE_TOOL_ROLL:          (_("Roll"), "tworoll_cursor.png"),
                    appconsts.TLINE_TOOL_SLIP:          (_("Slip"), "slide_cursor.png"),
                    appconsts.TLINE_TOOL_SPACER:        (_("Spacer"), "multimove_cursor.png"),
                    appconsts.TLINE_TOOL_BOX:           (_("Box"), "overwrite_cursor_box.png"),
                    appconsts.TLINE_TOOL_RIPPLE_TRIM:   (_("Ripple Trim"), "oneroll_cursor_ripple.png"),
                    appconsts.TLINE_TOOL_CUT:           (_("Cut"), "cut_cursor.png"),
                    appconsts.TLINE_TOOL_KFTOOL:        (_("Keyframe"), "kftool_cursor.png")
                  }
                  
    _TOOL_TIPS =  { appconsts.TLINE_TOOL_INSERT:        _("<b>Left Mouse</b> to move and insert single clip between clips.\n<b>CTRL + Left Mouse</b> to select and move clip range.\n<b>Left Mouse</b> on clip ends to trim clip length."),
                    appconsts.TLINE_TOOL_OVERWRITE:     _("<b>Left Mouse</b> to move clip into new position.\n<b>CTRL + Left Mouse</b> to select and move clip range into new position.\n<b>Left Mouse</b> on clip ends to trim clip length."),
                    appconsts.TLINE_TOOL_TRIM:          _("<b>Left Mouse</b> to trim closest clip end.\n<b>Left or Right Arrow Key</b> + <b>Enter Key</b> to do the edit using keyboard."), 
                    appconsts.TLINE_TOOL_ROLL:          _("<b>Left Mouse</b> to move closest edit point between 2 clips.\n<b>Left or Right Arrow Key</b> + <b>Enter Key</b> to do the edit using keyboard."), 
                    appconsts.TLINE_TOOL_SLIP:          _("<b>Left Mouse</b> to move clip contents within clip.\n<b>Left or Right Arrow Key</b> + <b>Enter Key</b> to do the edit using keyboard."), 
                    appconsts.TLINE_TOOL_SPACER:        _("<b>Left Mouse</b> to move clip under cursor and all clips after it forward or backward, overwrites not allowed.\n<b>CTRL + Left Mouse</b> to move clip under cursor and all clips after it <b>on the same track</b> forward or backward, overwrites not allowed."), 
                    appconsts.TLINE_TOOL_BOX:           _("<b>1. Left Mouse</b> to draw a box to select a group of clips.\n<b>2. Left Mouse</b> inside the box to move selected clips forward or backward."), 
                    appconsts.TLINE_TOOL_RIPPLE_TRIM:   _("<b>Left Mouse</b> to trim closest clip end and move all clips after it to maintain sync, overwrites not allowed.\n<b>Left or Right Arrow Key</b> + <b>Enter Key</b> to do the edit using keyboard."), 
                    appconsts.TLINE_TOOL_CUT:           _("<b>Left Mouse</b> to cut clip under cursor.\n<b>CTRL + Left Mouse</b> to cut clips on all tracks at cursor position."), 
                    appconsts.TLINE_TOOL_KFTOOL:        _("Keyframe")
                  }
#----------------------------------------------------- workflow presets
def _set_workflow_STANDARD():
    editorpersistance.prefs.active_tools = [2, 6, 8, 4, 5, 7]
    editorpersistance.prefs.dnd_action = appconsts.DND_ALWAYS_OVERWRITE
    editorpersistance.prefs.box_for_empty_press_in_overwrite_tool = True
    editorpersistance.save()

    modesetting.set_default_edit_mode()

def _set_workflow_FILM_STYLE():
    editorpersistance.prefs.active_tools = [1, 2, 3, 4, 5, 6, 7]
    editorpersistance.prefs.dnd_action = appconsts.DND_OVERWRITE_NON_V1
    editorpersistance.prefs.box_for_empty_press_in_overwrite_tool = False
    editorpersistance.save()

    modesetting.set_default_edit_mode()


# --------------------------------------------------------------- tools menu
def get_tline_tool_popup_menu(launcher, event, callback):
    menu = _tools_menu
    guiutils.remove_children(menu)

    menu.set_accel_group(gui.editor_window.accel_group)
    menu.set_take_focus(False)
    menu_items = []
    
    kb_shortcut_number = 1
    for tool_id in editorpersistance.prefs.active_tools:
        tool_name, tool_icon_file = _TOOLS_DATA[tool_id]

        menu_item = _get_image_menu_item(tool_icon_file, tool_name, callback, tool_id)
        accel_path = "<Actions>/WindowActions/TOOL_ACTION_KEY_" + str(kb_shortcut_number)
        menu_item.set_accel_path(accel_path)
        menu.add(menu_item)
        menu_items.append(menu_item)
        kb_shortcut_number = kb_shortcut_number + 1

    menu.connect("hide", lambda w : _tools_menu_hidden(w, menu_items))
    menu.show_all()
    menu.popup(None, None, None, None, event.button, event.time)

def _tools_menu_hidden(tools_menu, menu_items):
    # needed to make number 1-6 work elsewhere in the application
    for menu_item in menu_items:
        menu_item.set_accel_path(None)

def _get_image_menu_item(tool_icon_file, text, callback, tool_id):
    item = Gtk.ImageMenuItem()
    tool_img = Gtk.Image.new_from_file(respaths.IMAGE_PATH + tool_icon_file)
        
    item.set_image(tool_img)
    item.connect("activate", callback, tool_id)
    item.set_always_show_image(True)
    item.set_use_stock(False)
    item.set_label(text)
    item.set_tooltip_markup(_TOOL_TIPS[tool_id])
    item.show()
    return item
    
    
# ---------------------------------------------------- workflow menu
def workflow_menu_launched(widget, event):
    guiutils.remove_children(_workflow_menu)

    # ---- preset
    presets_item = Gtk.MenuItem.new_with_label(_("Workflow Presets"))
    presets_item.show()

    presets_menu = Gtk.Menu()
    
    standard = guiutils.get_menu_item(_("Standard"), _workflow_menu_callback, (None, "preset standard"))
    standard.show()
    presets_menu.add(standard)

    film_style = guiutils.get_menu_item(_("Film Style"), _workflow_menu_callback, (None, "preset filmstyle"))
    film_style.show()
    presets_menu.add(film_style)
    
    presets_item.set_submenu(presets_menu)
    _workflow_menu.add(presets_item)

    # --- behaviours
    guiutils.add_separetor(_workflow_menu)

    behaviours_item = Gtk.MenuItem.new_with_label(_("Behaviours"))
    behaviours_item.show()

    behaviours_menu = Gtk.Menu()
    
    delete_item = Gtk.MenuItem.new_with_label(_("Default Delete Action"))
    delete_item.show()

    delete_menu = Gtk.Menu()
    labels = [_("Lift"), _("Splice Out")]
    msgs = ["delete lift", "delete splice"]
    _build_radio_menu_items_group(delete_menu, labels, msgs, _workflow_menu_callback, 0)

    delete_item.set_submenu(delete_menu)
    behaviours_menu.add(delete_item)

    dnd_item = Gtk.MenuItem.new_with_label(_("Drag'n'Drop Action"))
    dnd_item.show()
    
    dnd_menu = Gtk.Menu()
    labels = [_("Always Overwrite Blanks"), _("Overwrite Blanks on non-V1 Tracks"), _("Always Insert")]
    msgs = ["always overwrite", "overwrite nonV1", "always insert"]
    active_index =  editorpersistance.prefs.dnd_action  #appconsts values corrspond with order here
    _build_radio_menu_items_group(dnd_menu, labels, msgs, _workflow_menu_callback, active_index)

    dnd_item.set_submenu(dnd_menu)
    behaviours_menu.add(dnd_item)

    autofollow_item = Gtk.CheckMenuItem()
    autofollow_item.set_label(_("Compositors Auto Follow"))
    autofollow_item.set_active(editorstate.auto_follow_active())
    autofollow_item.connect("activate", _workflow_menu_callback, (None, "autofollow"))
    autofollow_item.show()

    behaviours_menu.append(autofollow_item)
    
    behaviours_item.set_submenu(behaviours_menu)
    _workflow_menu.add(behaviours_item)

    # --- tools
    guiutils.add_separetor(_workflow_menu)
    
    # Active tools
    non_active_tools = range(1, 11) # we have 10 tools currently
    for i in range(0, len(editorpersistance.prefs.active_tools)):#  tool_id in _TOOLS_DATA:
        tool_id = editorpersistance.prefs.active_tools[i]
        tool_name, tool_icon_file = _TOOLS_DATA[tool_id]
        _workflow_menu.add(_get_workflow_tool_menu_item(_workflow_menu_callback, tool_id, tool_name, tool_icon_file, i+1))
        try: # needed to prevent crashes when manually changing preset tools during dev, remove when those are decided upon
            non_active_tools.remove(tool_id)
        except:
            pass

    guiutils.add_separetor(_workflow_menu)
    
    # Non-active tools
    for tool_id in non_active_tools:
        tool_name, tool_icon_file = _TOOLS_DATA[tool_id]
        _workflow_menu.add(_get_workflow_tool_menu_item(_workflow_menu_callback, tool_id, tool_name, tool_icon_file, -1))
        
    _workflow_menu.popup(None, None, None, None, event.button, event.time)

def _get_workflow_tool_menu_item(callback, tool_id, tool_name, tool_icon_file, position):

    tool_active = (tool_id in editorpersistance.prefs.active_tools)

    tool_img = Gtk.Image.new_from_file(respaths.IMAGE_PATH + tool_icon_file)
    tool_name_label = Gtk.Label(tool_name)
    
    hbox = Gtk.HBox()
    hbox.pack_start(guiutils.pad_label(4, 4), False, False, 0)
    hbox.pack_start(tool_img, False, False, 0)
    hbox.pack_start(guiutils.pad_label(4, 4), False, False, 0)
    hbox.pack_start(tool_name_label, False, False, 0)
    hbox.show_all()
    hbox.set_sensitive(tool_active)
    item = Gtk.MenuItem()
    item.add(hbox)
    item.show()
    
    item.set_submenu(_get_workflow_tool_submenu(callback, tool_id, position))

    return item

def _build_radio_menu_items_group(menu, labels, msgs, callback, active_index):
    first_item = Gtk.RadioMenuItem()
    first_item.set_label(labels[0])
    first_item.show()
    menu.append(first_item)
    if active_index == 0:
        first_item.set_active(True)
    first_item.connect("activate", callback, (None,msgs[0]))
    
    for i in range(1, len(labels)):
        radio_item = Gtk.RadioMenuItem.new_with_label([first_item], labels[i])
        menu.append(radio_item)
        radio_item.show()
        if active_index == i:
            radio_item.set_active(True)
        
        radio_item.connect("activate", callback, (None, msgs[i]))

def _get_workflow_tool_submenu(callback, tool_id, position):
    sub_menu = Gtk.Menu()
    
    tool_active = (tool_id in editorpersistance.prefs.active_tools)
    activity_item = Gtk.CheckMenuItem(_("Tool Active").encode('utf-8'))
    activity_item.set_active(tool_active)
    activity_item.connect("toggled", callback, (tool_id, "activity"))
    activity_item.show()
    sub_menu.add(activity_item)

    guiutils.add_separetor(sub_menu)
    
    position_item = Gtk.MenuItem.new_with_label(_("Set Position"))
    if tool_active == False:
        position_item.set_sensitive(False)
    position_item.show()

    position_menu = Gtk.Menu()
    
    for i in range(1, len(editorpersistance.prefs.active_tools) + 1):
        move_to_position_item = guiutils.get_menu_item(str(i), _workflow_menu_callback, (tool_id, str(i)))
        if i == position or position == -1:
            move_to_position_item.set_sensitive(False)
        move_to_position_item.show()
        position_menu.add(move_to_position_item)
        
    position_item.set_submenu(position_menu)

    sub_menu.add(position_item)
    
    # Individual prefs for tools
    if tool_id == appconsts.TLINE_TOOL_OVERWRITE:
        pref_item = Gtk.CheckMenuItem(_("Do Box Selection and Box Move from empty press").encode('utf-8'))
        pref_item.set_active(editorpersistance.prefs.box_for_empty_press_in_overwrite_tool)
        pref_item.connect("toggled", _TLINE_TOOL_OVERWRITE_box_selection_pref)
        pref_item.show()
        sub_menu.add(pref_item)
        guiutils.add_separetor(sub_menu)
        
    return sub_menu
    
def _workflow_menu_callback(widget, data):
    #print data
    #print editorpersistance.prefs.active_tools
    tool_id, msg = data

    if msg == "activity":
        if widget.get_active() == False:
            editorpersistance.prefs.active_tools.remove(tool_id)
        else:
            editorpersistance.prefs.active_tools.append(tool_id)
    elif msg == "preset standard":
        _set_workflow_STANDARD()
    elif msg == "preset filmstyle":
        _set_workflow_FILM_STYLE()
    elif msg == "autofollow":
        active = widget.get_active()
        editorstate.auto_follow = active
        PROJECT().set_project_property(appconsts.P_PROP_AUTO_FOLLOW, active)
        if active == True:
            # Do autofollow update if auto follow activated
            compositor_autofollow_data = edit.get_full_compositor_sync_data()
            edit.do_autofollow_redo(compositor_autofollow_data)
        updater.repaint_tline()
    elif  msg == "always overwrite":
        editorpersistance.prefs.dnd_action = appconsts.DND_ALWAYS_OVERWRITE
    elif  msg == "overwrite nonV1":
        editorpersistance.prefs.dnd_action = appconsts.DND_OVERWRITE_NON_V1
    elif  msg == "always insert":
        editorpersistance.prefs.dnd_action = appconsts.DND_ALWAYS_INSERT
    else:
        try:
            pos = int(msg)
            current_index = editorpersistance.prefs.active_tools.index(tool_id)
            editorpersistance.prefs.active_tools.remove(tool_id)
            editorpersistance.prefs.active_tools.insert(pos - 1, tool_id)
        except:
            pass
    
    editorpersistance.save()
    """ MAYBE ADD BACK
    elif msg == "pointer_sensitive_item":
        editorstate.cursor_is_tline_sensitive = widget.get_active()
    """

# ------------------------------------------------------------- keyboard shortcuts
def tline_tool_keyboard_selected(event):
  
    try:
        keyboard_number = int(Gdk.keyval_name(event.keyval).lower())
        tool_id = editorpersistance.prefs.active_tools[keyboard_number - 1]
        gui.editor_window.change_tool(tool_id)
        return True
    except:
        # This fails if not a valid number was pressed, so probably most times.
        pass
        
    return False


# -------------------------------------------------------------- tool prefs
def _TLINE_TOOL_OVERWRITE_box_selection_pref(check_menu_item):
    editorpersistance.prefs.box_for_empty_press_in_overwrite_tool = check_menu_item.get_active()
    editorpersistance.save()




class WorkflowDialog(Gtk.Dialog):

    def __init__(self):
        Gtk.Dialog.__init__(self, _("Welcome To Flowblade 2"),  None,
                                Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                (_("Select Preset Workflow and Continue").encode('utf-8'), Gtk.ResponseType.ACCEPT))
        
        self.DEFAULT_SELECTION = 1

        info_label_text_1 = _("To audio sync clips you need move action origin clip by ") # + str(data.clip_tline_media_offset - data.media_offset_frames) + _(" frames.")
        info_label_1 = Gtk.Label(info_label_text_1)

        info_label_text_2 = _("To audio sync clips you need move action origin clip by ") # + str(data.clip_tline_media_offset - data.media_offset_frames) + _(" frames.")
        info_label_2 = Gtk.Label(info_label_text_2)

        preset_workflow_text_1 = _("workflow 1 ") # + str(data.clip_tline_media_offset - data.media_offset_frames) + _(" frames.")
        workflow_select_item_1 = self.get_workflow_select_item(1, preset_workflow_text_1)

        preset_workflow_text_2 = _("workflow 2 ") # + str(data.clip_tline_media_offset - data.media_offset_frames) + _(" frames.")
        workflow_select_item_2 = self.get_workflow_select_item(2, preset_workflow_text_1)
        
        panel_vbox = Gtk.VBox(False, 2)
        panel_vbox.pack_start(guiutils.get_pad_label(24, 12), False, False, 0)
        panel_vbox.pack_start(guiutils.get_left_justified_box([info_label_1]), False, False, 0)
        panel_vbox.pack_start(workflow_select_item_1, False, False, 0)
        panel_vbox.pack_start(workflow_select_item_2, False, False, 0)
        panel_vbox.pack_start(info_label_2, False, False, 0)
        panel_vbox.pack_start(guiutils.get_pad_label(24, 24), False, False, 0)

        alignment = dialogutils.get_alignment2(panel_vbox)

        self.vbox.pack_start(alignment, True, True, 0)
        dialogutils.set_outer_margins(self.vbox)
        dialogs._default_behaviour(self)
        self.connect('response', self.done)
        self.show_all()

    def get_workflow_select_item(self, item_number, item_text):
        label = Gtk.Label(item_text)
        widget = Gtk.EventBox()
        widget.connect("button-press-event", lambda w,e: self.selected_callback(w, item_number))
        #widget.connect("button-release-event", lambda w,e: release_callback(self, w, e))
        widget.set_can_focus(True)
        widget.add_events(Gdk.EventMask.KEY_PRESS_MASK)

        widget.add(label)
        if item_number == self.DEFAULT_SELECTION:
            widget.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(0.1, 0.31, 0.58,1.0))
            
        return widget

    def done(self, dialog, response_id):
        dialog.destroy()

    def selected_callback(self, w, item_number):
        pass
