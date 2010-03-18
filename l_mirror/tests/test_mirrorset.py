#
# LMirror is Copyright (C) 2010 Robert Collins <robertc@robertcollins.net>
# 
# LMirror is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
# 
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# this program.  If not, see <http://www.gnu.org/licenses/>.
# 
# In the LMirror source tree the file COPYING.txt contains the GNU General Public
# License version 3.
# 

"""Tests for the mirrorset module."""

from doctest import ELLIPSIS

from bzrlib.transport import get_transport
from bzrlib.transport.memory import MemoryServer

from testtools.matchers import DocTestMatches

from l_mirror import mirrorset
from l_mirror.ui.model import UI
from l_mirror.tests import ResourcedTestCase


class TestMirrorSet(ResourcedTestCase):

    def get_test_ui(self):
        ui = UI()
        return ui

    def setup_memory(self):
        """Create a memory url server and return its url."""
        # XXX: integrate with ui.here better.
        self.transport_factory = MemoryServer()
        self.transport_factory.start_server()
        self.addCleanup(self.transport_factory.stop_server)
        return self.transport_factory.get_url()

    def test_create_set(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        t = basedir.clone('.lmirror/sets/myname')
        self.assertEqual('1\n', t.get_bytes('format'))
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = .
"""))
        self.assertEqual(basedir, mirror.base)
        self.assertEqual('myname', mirror.name)
        self.assertEqual(ui, mirror.ui)

    def test_accepts_content_root(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        contentdir = basedir.clone('../content')
        contentdir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', contentdir, ui)
        t = basedir.clone('.lmirror/sets/myname')
        self.assertEqual('1\n', t.get_bytes('format'))
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = ../content
"""))

    def test_second_set_does_not_error(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        mirror = mirrorset.initialise(basedir, 'myname2', basedir, ui)
        t = basedir.clone('.lmirror/sets/myname2')
        self.assertEqual('1\n', t.get_bytes('format'))
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = .
"""))

    def test_creates_metadata_dir(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        t = basedir.clone('.lmirror/metadata/myname')
        self.assertEqual('1\n', t.get_bytes('format'))
        self.assertThat(t.get_bytes('metadata.conf'), DocTestMatches("""[metadata]
basis = 0
latest = 0
timestamp = 0
updating = True
""", ELLIPSIS))
        self.assertThat(t.get_bytes('journals/0'), DocTestMatches("""l-mirror-journal-1
"""))

    def test_open_set(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirrorset.initialise(basedir, 'myname', basedir, ui)
        t = basedir.clone('.lmirror/sets/myname')
        self.assertEqual('1\n', t.get_bytes('format'))
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = .
"""))   
        mirror = mirrorset.MirrorSet(basedir, 'myname', ui)

    def test_open_missing(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        self.assertRaises(ValueError, mirrorset.MirrorSet, basedir, 'myname', ui)

    def test_open_wrong_format(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirrorset.initialise(basedir, 'myname', basedir, ui)
        t = basedir.clone('.lmirror/sets/myname')
        self.assertEqual('1\n', t.get_bytes('format'))
        t.put_bytes('format', '2\n')
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = .
"""))   
        self.assertRaises(ValueError, mirrorset.MirrorSet, basedir, 'myname', ui)

    def test_start_change_updating_error(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        self.assertRaises(ValueError, mirror.start_change)

    def test_start_change_not_updating_starts_change(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        mirror.finish_change()
        mirror.start_change()
        # We know finish_change errors if a change isn't open, so it working is
        # sufficient.
        mirror.finish_change()

    def test_finish_change_not_updating_error(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        mirror.finish_change()
        self.assertRaises(ValueError, mirror.finish_change)

    def test_finish_change_scans_content(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        basedir.create_prefix()
        basedir.mkdir('dir1')
        basedir.mkdir('dir2')
        basedir.put_bytes('abc', '1234567890\n')
        basedir.put_bytes('dir1/def', 'abcdef')
        mirror.finish_change()
        t = basedir.clone('.lmirror/metadata/myname')
        self.assertThat(t.get_bytes('metadata.conf'), DocTestMatches("""[metadata]
basis = 0
latest = 1
timestamp = ...
updating = False

""", ELLIPSIS))
        self.assertThat(t.get_bytes('journals/1'), DocTestMatches("""l-mirror-journal-1
.lmirror\x00new\x00dir\x00.lmirror/sets\x00new\x00dir\x00.lmirror/sets/myname\x00new\x00dir\x00.lmirror/sets/myname/format\x00new\x00file\x00e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e\x002\x00.lmirror/sets/myname/set.conf\x00new\x00file\x00061df21cf828bb333660621c3743cfc3a3b2bd23\x0023\x00abc\x00new\x00file\x0012039d6dd9a7e27622301e935b6eefc78846802e\x0011\x00dir1\x00new\x00dir\x00dir1/def\x00new\x00file\x001f8ac10f23c5b5bc1167bda84b833e5c057a77d2\x006\x00dir2\x00new\x00dir"""))
