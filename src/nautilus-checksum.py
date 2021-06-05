#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of nautilus-checksum
#
# Copyright (c) 2016 Lorenzo Carbonell Cerezo <a.k.a. atareao>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import gi
try:
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('GLib', '2.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('Nautilus', '3.0')
    gi.require_version('GObject', '2.0')
except Exception as e:
    print(e)
    exit(-1)
import os
import hashlib
import zlib
import locale
import gettext
from threading import Thread
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Nautilus as FileManager

APP = 'nautilus-checksum'
LANGDIR = os.path.join('usr', 'share', 'locale-langpack')
APPNAME = 'nautilus-checksum'
ICON = 'nautilus-checksum'
VERSION = '0.1.0'
BLOCKSIZE = 65536

try:
    current_locale, encoding = locale.getdefaultlocale()
    language = gettext.translation(APP, LANGDIR, [current_locale])
    language.install()
    _ = language.gettext
except:
    _ = str


def hash_bytestr_iter(bytesiter, hasher, ashexstr=True):
    for block in bytesiter:
        hasher.update(block)
    return hasher.hexdigest() if ashexstr else hasher.digest()


def file_as_blockiter(afile, blocksize=BLOCKSIZE):
    with afile:
        block = afile.read(blocksize)
        while len(block) > 0:
            yield block
            block = afile.read(blocksize)


class ChecksumDialog(Gtk.Dialog):

    def __init__(self, parent, afile):
        Gtk.Dialog.__init__(self, _('Checksum'), parent)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.add_button(Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT)
        self.connect('realize', self.on_realize)

        frame = Gtk.Frame()
        frame.set_border_width(5)
        grid = Gtk.Grid()
        grid.set_border_width(5)
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        frame.add(grid)
        self.get_content_area().add(frame)

        label00 = Gtk.Label.new(_('File')+' :')
        label00.set_xalign(0)
        grid.attach(label00, 0, 0, 1, 1)
        label10 = Gtk.Label.new(_('MD5 checksum')+' :')
        label10.set_xalign(0)
        grid.attach(label10, 0, 1, 1, 1)
        label20 = Gtk.Label.new(_('SHA1 checksum')+' :')
        label20.set_xalign(0)
        grid.attach(label20, 0, 2, 1, 1)
        label30 = Gtk.Label.new(_('SHA256 checksum')+' :')
        label30.set_xalign(0)
        grid.attach(label30, 0, 3, 1, 1)
        label40 = Gtk.Label.new(_('SHA512 checksum')+' :')
        label40.set_xalign(0)
        grid.attach(label40, 0, 4, 1, 1)
        label50 = Gtk.Label.new(_('CRC')+' :')
        label50.set_xalign(0)
        grid.attach(label50, 0, 5, 1, 1)

        self.entry01 = Gtk.Entry()
        self.entry01.set_width_chars(70)
        self.entry01.set_property("editable", False)
        grid.attach(self.entry01, 1, 0, 1, 1)

        self.entry11 = Gtk.Entry()
        self.entry11.set_property("editable", False)
        grid.attach(self.entry11, 1, 1, 1, 1)

        button11 = Gtk.Button.new_from_icon_name('edit-copy',
                                                 Gtk.IconSize.BUTTON)
        button11.connect('clicked', self.on_clicked, self.entry11)
        grid.attach(button11, 2, 1, 1, 1)

        self.entry21 = Gtk.Entry()
        self.entry21.set_property("editable", False)
        grid.attach(self.entry21, 1, 2, 1, 1)

        button21 = Gtk.Button.new_from_icon_name('edit-copy',
                                                 Gtk.IconSize.BUTTON)
        button21.connect('clicked', self.on_clicked, self.entry21)
        grid.attach(button21, 2, 2, 1, 1)

        self.entry31 = Gtk.Entry()
        self.entry31.set_property("editable", False)
        grid.attach(self.entry31, 1, 3, 1, 1)

        button31 = Gtk.Button.new_from_icon_name('edit-copy',
                                                 Gtk.IconSize.BUTTON)
        button31.connect('clicked', self.on_clicked, self.entry31)
        grid.attach(button31, 2, 3, 1, 1)

        self.entry41 = Gtk.Entry()
        self.entry41.set_property("editable", False)
        grid.attach(self.entry41, 1, 4, 1, 1)

        button41 = Gtk.Button.new_from_icon_name('edit-copy',
                                                 Gtk.IconSize.BUTTON)
        button41.connect('clicked', self.on_clicked, self.entry41)
        grid.attach(button41, 2, 4, 1, 1)

        self.entry51 = Gtk.Entry()
        self.entry51.set_property("editable", False)
        grid.attach(self.entry51, 1, 5, 1, 1)

        button51 = Gtk.Button.new_from_icon_name('edit-copy',
                                                 Gtk.IconSize.BUTTON)
        button51.connect('clicked', self.on_clicked, self.entry51)
        grid.attach(button51, 2, 5, 1, 1)

        self.show_all()

        self.calculate_checksum(afile)

    def on_clicked(self, widget, entry):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(entry.get_text(), -1)

    def calculate_checksum(self, afile):
        diib = DoItInBackground(afile)
        progreso = Progreso(_('Calculate checksums'), self, 5)
        progreso.connect('i-want-stop', diib.stopit)
        diib.connect('started', progreso.set_max_value)
        diib.connect('end_one', progreso.increase)
        diib.connect('start_one', progreso.set_element)
        diib.connect('ended', progreso.close)
        diib.connect('file', self.update_value_01)
        diib.connect('md5', self.update_value_11)
        diib.connect('sha1', self.update_value_21)
        diib.connect('sha256', self.update_value_31)
        diib.connect('sha512', self.update_value_41)
        diib.connect('crc', self.update_value_51)
        diib.start()
        progreso.run()

    def close(self, *args):
        self.destroy()

    def update_value_01(self, anobject, value):
        self.entry01.set_text(value)

    def update_value_11(self, anobject, value):
        self.entry11.set_text(value)

    def update_value_21(self, anobject, value):
        self.entry21.set_text(value)

    def update_value_31(self, anobject, value):
        self.entry31.set_text(value)

    def update_value_41(self, anobject, value):
        self.entry41.set_text(value)

    def update_value_51(self, anobject, value):
        self.entry51.set_text(value)

    def on_realize(self, *_):
        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        pointer = seat.get_pointer()
        screen, x, y = pointer.get_position()
        monitor = display.get_monitor_at_point(x, y)
        scale = monitor.get_scale_factor()
        monitor_width = monitor.get_geometry().width / scale
        monitor_height = monitor.get_geometry().height / scale
        width = self.get_preferred_width()[0]
        height = self.get_preferred_height()[0]
        self.move((monitor_width - width)/2, (monitor_height - height)/2)


def get_hashsum(algorithm, afile):
    if algorithm == 'md5':
        hashsum = hashlib.md5()
    elif algorithm == 'sha1':
        hashsum = hashlib.sha1()
    elif algorithm == 'sha256':
        hashsum = hashlib.sha256()
    elif algorithm == 'sha512':
        hashsum = hashlib.sha512()
    elif algorithm == 'crc':
        prev = 0
        for eachLine in open(afile, 'rb'):
            prev = zlib.crc32(eachLine, prev)
        return "%X" % (prev & 0xFFFFFFFF)
    else:
        return ''
    return hash_bytestr_iter(file_as_blockiter(open(afile, 'rb')), hashsum)


class IdleObject(GObject.GObject):
    """
    Override GObject.GObject to always emit signals in the main thread
    by emmitting on an idle handler
    """
    def __init__(self):
        GObject.GObject.__init__(self)

    def emit(self, *args):
        GLib.idle_add(GObject.GObject.emit, self, *args)


class DoItInBackground(IdleObject, Thread):
    __gsignals__ = {
        'started': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'ended': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, ()),
        'start_one': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'end_one': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'file': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'md5': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'sha1': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'sha256': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'sha512': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'crc': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (str,)),
    }

    def __init__(self, afile):
        IdleObject.__init__(self)
        Thread.__init__(self)
        self.daemon = True
        self.afile = afile
        self.iwts = False

    def stopit(self, *arg):
        self.iwts = True
        exit(0)

    def run(self):
        self.emit('started', 5)
        self.calculate(self.afile)
        self.emit('ended')

    def calculate(self, afile):
        if afile is not None:
            self.emit('file', afile)
            if self.iwts is True:
                return
            self.emit('start_one', 'md5')
            hassum = get_hashsum('md5', afile)
            self.emit('md5', hassum)
            self.emit('end_one', 1)
            if self.iwts is True:
                return
            self.emit('start_one', 'sha1')
            hassum = get_hashsum('sha1', afile)
            self.emit('sha1', hassum)
            self.emit('end_one', 1)
            if self.iwts is True:
                return
            self.emit('start_one', 'sha256')
            hassum = get_hashsum('sha256', afile)
            self.emit('sha256', hassum)
            self.emit('end_one', 1)
            if self.iwts is True:
                return
            self.emit('start_one', 'sha512')
            hassum = get_hashsum('sha512', afile)
            self.emit('sha512', hassum)
            self.emit('end_one', 1)
            if self.iwts is True:
                return
            self.emit('start_one', 'crc')
            hassum = get_hashsum('crc', afile)
            self.emit('crc', hassum)
            self.emit('end_one', 1)
            if self.iwts is True:
                return


def get_files(files_in):
    files = []
    for file_in in files_in:
        if not file_in.is_directory():
            files.append(file_in.get_location().get_path())
    return files


class Progreso(Gtk.Dialog, IdleObject):
    __gsignals__ = {
        'i-want-stop': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, title, parent, max_value):
        Gtk.Dialog.__init__(self, title, parent)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        IdleObject.__init__(self)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(330, 30)
        self.set_resizable(False)
        self.connect('destroy', self.close)
        self.set_modal(True)
        vbox = Gtk.VBox(spacing=5)
        vbox.set_border_width(5)
        self.get_content_area().add(vbox)

        frame1 = Gtk.Frame()
        vbox.pack_start(frame1, True, True, 0)
        grid = Gtk.Grid()
        grid.set_margin_top(20)
        grid.set_margin_bottom(20)
        grid.set_margin_start(20)
        grid.set_margin_end(20)
        frame1.add(grid)

        self.label = Gtk.Label.new()
        grid.attach(self.label, 0, 0, 2, 1)

        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_size_request(300, 0)
        grid.attach(self.progressbar, 0, 1, 3, 1)

        button_stop = Gtk.Button()
        button_stop.set_size_request(40, 40)
        button_stop.set_image(
            Gtk.Image.new_from_icon_name(Gtk.STOCK_STOP, Gtk.IconSize.BUTTON))
        button_stop.connect('clicked', self.on_button_stop_clicked)
        grid.attach(button_stop, 3, 0, 1, 1)

        self.stop = False
        self.show_all()
        self.max_value = max_value
        self.value = 0.0

    def set_max_value(self, anobject, max_value):
        self.max_value = float(max_value)

    def get_stop(self):
        return self.stop

    def on_button_stop_clicked(self, widget):
        self.stop = True
        self.emit('i-want-stop')

    def close(self, *args):
        self.emit('i-want-stop')
        self.destroy()

    def set_element(self, anobject, element):
        self.label.set_text(_('Calculating: %s') % element)

    def increase(self, anobject, value):
        self.value += float(value)
        fraction = self.value/self.max_value
        self.progressbar.set_fraction(fraction)
        if self.value == self.max_value:
            self.hide()


class ChecksumFileMenuProvider(GObject.GObject, FileManager.MenuProvider):
    """
    Implements the 'Replace in Filenames' extension to the File Manager\
    right-click menu
    """

    def __init__(self):
        """
        File Manager crashes if a plugin doesn't implement the __init__\
        method
        """
        GObject.Object.__init__(self)

    def the_first_is_file(self, items):
        if len(items) > 0:
            if items[0].is_directory():
                return False
            return True
        return False

    def hashcheck(self, menu, window, selected):
        files = get_files(selected)
        if len(files) > 0:
            hsd = ChecksumDialog(window, files[0])
            hsd.run()
            hsd.destroy()

    def get_file_items(self, window, sel_items):
        """
        Adds the 'Replace in Filenames' menu item to the File Manager\
        right-click menu, connects its 'activate' signal to the 'run'\
        method passing the selected Directory/File
        """
        if self.the_first_is_file(sel_items):
            top_menuitem = FileManager.MenuItem(
                name='ChecksumFileMenuProvider::Gtk-checksum-top',
                label=_('Checksum'),
                tip=_('Get checksum for file'))
            submenu = FileManager.Menu()
            top_menuitem.set_submenu(submenu)

            sub_menuitem_00 = FileManager.MenuItem(
                name='ChecksumFileMenuProvider::Gtk-checksum-sub-00',
                label=_('Checksum') + '...',
                tip=_('Get checksum for file'))
            sub_menuitem_00.connect('activate', self.hashcheck, window,
                                    sel_items)
            submenu.append_item(sub_menuitem_00)

            sub_menuitem_01 = FileManager.MenuItem(
                name='ChecksumFileMenuProvider::Gtk-500px-sub-02',
                label=_('About'),
                tip=_('About'))
            sub_menuitem_01.connect('activate', self.about, window)
            submenu.append_item(sub_menuitem_01)

            return top_menuitem,
        return

    def about(self, widget, window):
        ad = Gtk.AboutDialog(parent=window)
        ad.set_name(APPNAME)
        ad.set_version(VERSION)
        ad.set_copyright('Copyrignt (c) 2016\nLorenzo Carbonell')
        ad.set_comments(APPNAME)
        ad.set_license('''
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
''')
        ad.set_website('http://www.atareao.es')
        ad.set_website_label('http://www.atareao.es')
        ad.set_authors(['Lorenzo Carbonell Cerezo <a.k.a. atareao>'])
        ad.set_documenters(['Lorenzo Carbonell Cerezo <a.k.a. atareao>'])
        ad.set_icon_name(ICON)
        ad.set_logo_icon_name(APPNAME)
        ad.run()
        ad.destroy()


if __name__ == '__main__':
    afile = '/home/lorenzo/Descargas/ejemplo.jpg'
    '''
    print(get_hashsum('md5', afile))
    print(get_hashsum('crc', afile))
    print(get_hashsum('sha1', afile))
    print(get_hashsum('sha256', afile))
    print(get_hashsum('sha512', afile))
    '''
    hsd = ChecksumDialog(None, afile)
    hsd.run()
    hsd.destroy()
