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
from gi.repository import GLib
from gi.repository import Nautilus as FileManager


SEPARATOR = u'\u2015' * 10

_ = str


class ChecksumDialog(Gtk.Dialog):

    def __init__(self, afile=None):
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
        entry01 = Gtk.Entry()
        entry01.set_width_chars(70)
        entry01.set_property("editable", False)
        entry01.connect('key-press-event', self.on_key_press)
        grid.attach(entry01, 1, 0, 1, 1)
        entry11 = Gtk.Entry()
        entry11.set_property("editable", False)
        entry11.connect('key-press-event', self.on_key_press)
        grid.attach(entry11, 1, 1, 1, 1)
        entry21 = Gtk.Entry()
        entry21.set_property("editable", False)
        entry21.connect('key-press-event', self.on_key_press)
        grid.attach(entry21, 1, 2, 1, 1)
        entry31 = Gtk.Entry()
        entry31.set_property("editable", False)
        entry31.connect('key-press-event', self.on_key_press)
        grid.attach(entry31, 1, 3, 1, 1)
        entry41 = Gtk.Entry()
        entry41.set_property("editable", False)
        entry41.connect('key-press-event', self.on_key_press)
        grid.attach(entry41, 1, 4, 1, 1)
        entry51 = Gtk.Entry()
        entry51.set_property("editable", False)
        entry51.connect('key-press-event', self.on_key_press)
        grid.attach(entry51, 1, 5, 1, 1)
        if afile is not None:
            entry01.set_text(afile)
            entry11.set_text(get_hashsum('md5', afile))
            entry21.set_text(get_hashsum('sha1', afile))
            entry31.set_text(get_hashsum('sha256', afile))
            entry41.set_text(get_hashsum('sha512', afile))
            entry51.set_text(get_hashsum('crc', afile))

        self.show_all()

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
        'started': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
        'ended': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (bool,)),
        'start_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (str,)),
        'end_one': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, elements):
        IdleObject.__init__(self)
        Thread.__init__(self)
        self.elements = elements
        self.stopit = False
        self.ok = True
        self.daemon = True
        self.process = None

    def stop(self, *args):
        self.stopit = True

    def crush_file(self, file_in):
        rutine = 'srm -lvr "%s"' % (file_in)
        args = shlex.split(rutine)
        self.process = subprocess.Popen(args, stdout=subprocess.PIPE)
        out, err = self.process.communicate()

    def run(self):
        self.emit('started')
        try:
            for element in self.elements:
                print(element)
                if self.stopit is True:
                    self.ok = False
                    break
                self.emit('start_one', element)
                self.crush_file(element)
                self.emit('end_one')
        except Exception as e:
            self.ok = False
        try:
            if self.process is not None:
                self.process.terminate()
                self.process = None
        except Exception as e:
            print(e)
        self.emit('ended', self.ok)


class Progreso(Gtk.Dialog, IdleObject):
    __gsignals__ = {
        'i-want-stop': (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, title, parent, max_value):
        Gtk.Dialog.__init__(self, title, parent)
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

    def get_stop(self):
        return self.stop

    def on_button_stop_clicked(self, widget):
        self.stop = True
        self.emit('i-want-stop')

    def close(self, *args):
        self.destroy()

    def set_element(self, anobject, element):
        self.label.set_text(_('Crushing: %s') % element)

    def increase(self, anobject):
        self.value += 1.0
        fraction = self.value/self.max_value
        self.progressbar.set_fraction(fraction)
        if self.value == self.max_value:
            self.hide()


def get_files(files_in):
    files = []
    for file_in in files_in:
        print(file_in)
        file_in = unquote_plus(file_in.get_uri()[7:])
        if os.path.isfile(file_in):
            files.append(file_in)
    return files


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
        file_in = unquote_plus(items[0].get_uri()[7:])
        if not os.path.isfile(file_in):
            return False
        return True

    def hashcheck(self, menu, selected):
        files = get_files(selected)
        csd = checksum(files[0])
        csd.run()

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
    print(hashlib.algorithms_available)
    afile = '/home/lorenzo/speeds.pdf'
    print(get_hashsum('md5', afile))
    print(get_hashsum('crc', afile))
    print(get_hashsum('sha1', afile))
    print(get_hashsum('sha256', afile))
    print(get_hashsum('sha512', afile))
    hsd = ChecksumDialog(afile)
    hsd.run()
