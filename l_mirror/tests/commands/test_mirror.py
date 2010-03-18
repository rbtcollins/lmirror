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

"""Tests for the mirror command."""

from doctest import ELLIPSIS

from bzrlib.transport import get_transport
from bzrlib.transport.memory import MemoryServer

from testtools.matchers import DocTestMatches

from l_mirror.commands import mirror
from l_mirror import mirrorset
from l_mirror.ui.model import UI
from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.matchers import MatchesException


class TestCommandCommands(ResourcedTestCase):

    def get_test_ui_and_cmd(self, args):
        ui = UI(args=args)
        cmd = mirror.mirror(ui)
        ui.set_command(cmd)
        return ui, cmd

    def setup_memory(self):
        """Create a memory url server and return its url."""
        # XXX: integrate with ui.here better.
        self.transport_factory = MemoryServer()
        self.transport_factory.start_server()
        self.addCleanup(self.transport_factory.stop_server)
        return self.transport_factory.get_url()

    def test_error_no_source(self):
        base = self.setup_memory()
        source = base + 'path/myname'
        target = base + 'clone'
        ui, cmd = self.get_test_ui_and_cmd((source, target))
        self.assertEqual(3, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('error', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1],
            MatchesException(ValueError("No set 'myname' - file not found")))

    def test_mirrors_new(self):
        base = self.setup_memory()
        source = base + 'path/myname'
        target = base + 'clone'
        t = get_transport(source).clone('..')
        t.create_prefix()
        t.mkdir('something blue')
        ui, cmd = self.get_test_ui_and_cmd((source, target))
        mirror = mirrorset.initialise(t, 'myname', t, ui)
        mirror.finish_change()
        self.assertEqual(0, cmd.execute())
        self.assertTrue(t.has('../clone/something blue'))
        target = mirrorset.MirrorSet(t.clone('../clone'), 'myname', ui)

    def test_mirrors_incremental(self):
        base = self.setup_memory()
        source = base + 'path/myname'
        target = base + 'clone'
        t = get_transport(source).clone('..')
        t.create_prefix()
        t.mkdir('something blue')
        clone_t = t.clone('../clone')
        clone_t.create_prefix()
        ui, cmd = self.get_test_ui_and_cmd((source, target))
        mirror = mirrorset.initialise(t, 'myname', t, ui)
        mirror.finish_change()
        target = mirrorset.initialise(clone_t, 'myname', clone_t, ui)
        target.cancel_change()
        target.receive(mirror)
        mirror.start_change()
        t.mkdir('something borrowed')
        mirror.finish_change()
        self.assertEqual(0, cmd.execute())
        self.assertTrue(clone_t.has('something borrowed'))
