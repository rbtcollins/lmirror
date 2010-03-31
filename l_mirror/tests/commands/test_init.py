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

"""Tests for the init command."""

from doctest import ELLIPSIS

from bzrlib.transport import get_transport

from testtools.matchers import DocTestMatches

from l_mirror.commands import init
from l_mirror import mirrorset
from l_mirror.ui.model import UI
from l_mirror.tests import ResourcedTestCase


class TestCommandCommands(ResourcedTestCase):

    def get_test_ui_and_cmd(self, args, options=()):
        ui = UI(args=args, options=options)
        cmd = init.init(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_creates_set_directory(self):
        base = self.setup_memory()
        root = base + 'path/myname'
        t = get_transport(base)
        t.mkdir('path')
        ui, cmd = self.get_test_ui_and_cmd((root,))
        self.assertEqual(0, cmd.execute())
        mirror = mirrorset.MirrorSet(t.clone('path'), 'myname', ui)

    def test_accepts_content_root(self):
        base = self.setup_memory()
        t = get_transport(base)
        t.mkdir('path')
        t.mkdir('content')
        root = base + 'path/myname'
        ui, cmd = self.get_test_ui_and_cmd((root, base + 'content'))
        self.assertEqual(0, cmd.execute())
        t = t.clone('path/.lmirror/sets/myname')
        # TODO make this accessible via MirrorSet object.
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = ../content
"""))

    def test_empty_does_not_scan(self):
        base = self.setup_memory()
        root = base + 'path/myname'
        t = get_transport(base)
        t = t.clone('path')
        contentdir = t
        contentdir.create_prefix()
        contentdir.mkdir('dir1')
        contentdir.mkdir('dir2')
        contentdir.put_bytes('abc', '1234567890\n')
        contentdir.put_bytes('dir1/def', 'abcdef')
        ui, cmd = self.get_test_ui_and_cmd((root,), [('empty', True)])
        self.assertEqual(0, cmd.execute())
        t = t.clone('.lmirror/metadata/myname')
        self.assertThat(t.get_bytes('metadata.conf'), DocTestMatches("""[metadata]
basis = 0
latest = 0
timestamp = ...
updating = True
""", ELLIPSIS))
        self.assertThat(t.get_bytes('journals/0'), DocTestMatches("""l-mirror-journal-2
"""))

    def test_scans_content_root(self):
        base = self.setup_memory()
        root = base + 'path/myname'
        t = get_transport(base)
        t = t.clone('path')
        contentdir = t
        contentdir.create_prefix()
        contentdir.mkdir('dir1')
        contentdir.mkdir('dir2')
        contentdir.put_bytes('abc', '1234567890\n')
        contentdir.put_bytes('dir1/def', 'abcdef')
        ui, cmd = self.get_test_ui_and_cmd((root,))
        self.assertEqual(0, cmd.execute())
        t = t.clone('.lmirror/metadata/myname')
        self.assertThat(t.get_bytes('metadata.conf'), DocTestMatches("""[metadata]
basis = 0
latest = 1
timestamp = ...
updating = False

""", ELLIPSIS))
        self.assertThat(t.get_bytes('journals/0'), DocTestMatches("""l-mirror-journal-2
"""))
        self.assertThat(t.get_bytes('journals/1'), DocTestMatches("""l-mirror-journal-2
.lmirror\x00new\x00dir\x00.lmirror/sets\x00new\x00dir\x00.lmirror/sets/myname\x00new\x00dir\x00.lmirror/sets/myname/format\x00new\x00file\x00e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e\x002\x000.000000\x00.lmirror/sets/myname/set.conf\x00new\x00file\x00061df21cf828bb333660621c3743cfc3a3b2bd23\x0023\x000.000000\x00abc\x00new\x00file\x0012039d6dd9a7e27622301e935b6eefc78846802e\x0011\x000.000000\x00dir1\x00new\x00dir\x00dir1/def\x00new\x00file\x001f8ac10f23c5b5bc1167bda84b833e5c057a77d2\x006\x000.000000\x00dir2\x00new\x00dir"""))
