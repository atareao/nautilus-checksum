#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file is part of nautilus-convert2ogg
#
# Copyright (C) 2012-2016 Lorenzo Carbonell
# lorenzo.carbonell.cerezo@gmail.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
#
import gi
try:
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    gi.require_version('Nautilus', '3.0')
except Exception as e:
    print(e)
    exit(-1)
import os
import hashlib
import zlib
from threading import Thread
from urllib import unquote_plus
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Nautilus as FileManager


SEPARATOR = u'\u2015' * 10

_ = str


class ChecksumDialog(Gtk.Dialog):

    def __init__(self, afile):
        Gtk.Dialog.__init__(self, _('Checksum'), None,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT,
                            (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)

        frame = Gtk.Frame()
        frame.set_border_width(5)
        grid = Gtk.Grid()
        grid.set_border_width(5)
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        frame.add(grid)
        self.get_content_area().add(frame)

        label00 = Gtk.Label(_('File')+' :')
        label00.set_xalign(0)
        grid.attach(label00, 0, 0, 1, 1)
        label10 = Gtk.Label(_('MD5 checksum')+' :')
        label10.set_xalign(0)
        grid.attach(label10, 0, 1, 1, 1)
        label20 = Gtk.Label(_('SHA1 checksum')+' :')
        label20.set_xalign(0)
        grid.attach(label20, 0, 2, 1, 1)
        label30 = Gtk.Label(_('SHA256 checksum')+' :')
        label30.set_xalign(0)
        grid.attach(label30, 0, 3, 1, 1)
        label40 = Gtk.Label(_('SHA512 checksum')+' :')
        label40.set_xalign(0)
        grid.attach(label40, 0, 4, 1, 1)
        label50 = Gtk.Label(_('CRC')+' :')
        label50.set_xalign(0)
        grid.attach(label50, 0, 5, 1, 1)
        self.entry01 = Gtk.Entry()
        self.entry01.set_width_chars(70)
        self.entry01.set_property("editable", False)
        self.entry01.connect('key-press-event', self.on_key_press)
        grid.attach(self.entry01, 1, 0, 1, 1)
        self.entry11 = Gtk.Entry()
        self.entry11.set_property("editable", False)
        self.entry11.connect('key-press-event', self.on_key_press)
        grid.attach(self.entry11, 1, 1, 1, 1)
        self.entry21 = Gtk.Entry()
        self.entry21.set_property("editable", False)
        self.entry21.connect('key-press-event', self.on_key_press)
        grid.attach(self.entry21, 1, 2, 1, 1)
        self.entry31 = Gtk.Entry()
        self.entry31.set_property("editable", False)
        self.entry31.connect('key-press-event', self.on_key_press)
        grid.attach(self.entry31, 1, 3, 1, 1)
        self.entry41 = Gtk.Entry()
        self.entry41.set_property("editable", False)
        self.entry41.connect('key-press-event', self.on_key_press)
        grid.attach(self.entry41, 1, 4, 1, 1)
        self.entry51 = Gtk.Entry()
        self.entry51.set_property("editable", False)
        self.entry51.connect('key-press-event', self.on_key_press)
        grid.attach(self.entry51, 1, 5, 1, 1)
        self.show_all()

        self.calculate_checksum(afile)

    def calculate_checksum(self, afile):
        diib = DoItInBackground(afile)
        progreso = Progreso(_('Calculate checksums'), self, 5)
        progreso.connect('i-want-stop', self.close)
        diib.connect('ended', self.update_checksum)
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
        exit()

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

    def update_checksum(self, anobject, data):
        self.entry01.set_text(data['file'])
        self.entry11.set_text(data['md5'])
        self.entry21.set_text(data['sha1'])
        self.entry31.set_text(data['sha256'])
        self.entry41.set_text(data['sha512'])
        self.entry51.set_text(data['crc'])

    def on_key_press(self, widget, anevent):
        if anevent.keyval == 65421 or anevent.keyval == 65293:
            self.response(Gtk.ResponseType.ACCEPT)


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
    with open(afile, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), ''):
            hashsum.update(chunk)
    f.close()
    return hashsum.hexdigest()


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
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (object,)),
        'start_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'end_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (int,)),
        'file': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'md5': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'sha1': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'sha256': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'sha512': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'crc': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
    }

    def __init__(self, afile):
        IdleObject.__init__(self)
        Thread.__init__(self)
        self.daemon = True
        self.afile = afile

    def run(self):
        self.emit('started', 5)
        ans = self.calculate(self.afile)
        print(ans)
        self.emit('ended', ans)

    def calculate(self, afile):
        ans = {}
        if afile is not None:
            ans['file'] = afile
            self.emit('file', afile)
            self.emit('start_one', 'md5')
            ans['md5'] = get_hashsum('md5', afile)
            self.emit('md5', ans['md5'])
            self.emit('end_one', 1)
            self.emit('start_one', 'sha1')
            ans['sha1'] = get_hashsum('sha1', afile)
            self.emit('sha1', ans['sha1'])
            self.emit('end_one', 1)
            self.emit('start_one', 'sha256')
            ans['sha256'] = get_hashsum('sha256', afile)
            self.emit('sha256', ans['sha256'])
            self.emit('end_one', 1)
            self.emit('start_one', 'sha512')
            ans['sha512'] = get_hashsum('sha512', afile)
            self.emit('sha512', ans['sha512'])
            self.emit('end_one', 1)
            self.emit('start_one', 'crc')
            ans['crc'] = get_hashsum('crc', afile)
            self.emit('crc', ans['crc'])
            self.emit('end_one', 1)
        else:
            ans['file'] = ''
            ans['md5'] = ''
            ans['sha1'] = ''
            ans['sha256'] = ''
            ans['sha512'] = ''
            ans['crc'] = ''
        return ans


def get_files(files_in):
    files = []
    for file_in in files_in:
        print(file_in)
        file_in = unquote_plus(file_in.get_uri()[7:])
        if os.path.isfile(file_in):
            files.append(file_in)
    return files


class Progreso(Gtk.Dialog, IdleObject):
    __gsignals__ = {
        'i-want-stop': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, title, parent, max_value):
        print(parent)
        Gtk.Dialog.__init__(self, title, parent,
                            Gtk.DialogFlags.MODAL |
                            Gtk.DialogFlags.DESTROY_WITH_PARENT)
        IdleObject.__init__(self)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_size_request(330, 30)
        self.set_resizable(False)
        self.connect('destroy', self.close)
        self.set_modal(True)
        vbox = Gtk.VBox(spacing=5)
        vbox.set_border_width(5)
        self.get_content_area().add(vbox)
        #
        frame1 = Gtk.Frame()
        vbox.pack_start(frame1, True, True, 0)
        table = Gtk.Table(2, 2, False)
        frame1.add(table)
        #
        self.label = Gtk.Label()
        table.attach(self.label, 0, 2, 0, 1,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK,
                     yoptions=Gtk.AttachOptions.EXPAND)
        #
        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_size_request(300, 0)
        table.attach(self.progressbar, 0, 1, 1, 2,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK,
                     yoptions=Gtk.AttachOptions.EXPAND)
        button_stop = Gtk.Button()
        button_stop.set_size_request(40, 40)
        button_stop.set_image(
            Gtk.Image.new_from_stock(Gtk.STOCK_STOP, Gtk.IconSize.BUTTON))
        button_stop.connect('clicked', self.on_button_stop_clicked)
        table.attach(button_stop, 1, 2, 1, 2,
                     xpadding=5,
                     ypadding=5,
                     xoptions=Gtk.AttachOptions.SHRINK)
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
        pass

    def the_first_is_file(self, items):
        if len(items) > 0:
            file_in = unquote_plus(items[0].get_uri()[7:])
            if not os.path.isfile(file_in):
                return False
            return True
        return False

    def hashcheck(self, menu, selected):
        files = get_files(selected)
        if len(files) > 0:
            hsd = ChecksumDialog(files[0])
            hsd.run()

    def get_file_items(self, window, sel_items):
        """
        Adds the 'Replace in Filenames' menu item to the File Manager\
        right-click menu, connects its 'activate' signal to the 'run'\
        method passing the selected Directory/File
        """
        if self.the_first_is_file(sel_items):
            top_menuitem = FileManager.MenuItem(
                name='ChecksumFileMenuProvider::Gtk-checksum-files',
                label=_('Checksum') + '...',
                tip=_('Get checksum for file'))
            top_menuitem.connect('activate', self.hashcheck, sel_items)
            #
            return top_menuitem,
        return


if __name__ == '__main__':
    afile = '/home/lorenzo/Descargas/ubuntu-gnome-16.10-desktop-amd64.iso'
    '''
    print(get_hashsum('md5', afile))
    print(get_hashsum('crc', afile))
    print(get_hashsum('sha1', afile))
    print(get_hashsum('sha256', afile))
    print(get_hashsum('sha512', afile))
    '''
    hsd = ChecksumDialog(afile)
    hsd.run()
