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

"""Tests for the start-change command."""

from doctest import ELLIPSIS

from bzrlib.transport import get_transport
from bzrlib.transport.memory import MemoryServer

from testtools.matchers import DocTestMatches

from l_mirror.commands import start_change
from l_mirror import mirrorset
from l_mirror.ui.model import UI
from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.matchers import MatchesException


class TestCommandStartChange(ResourcedTestCase):

    def get_test_ui_and_cmd(self, args):
        ui = UI(args=args)
        cmd = start_change.start_change(ui)
        ui.set_command(cmd)
        return ui, cmd

    def setup_memory(self):
        """Create a memory url server and return its url."""
        # XXX: integrate with ui.here better.
        self.transport_factory = MemoryServer()
        self.transport_factory.start_server()
        self.addCleanup(self.transport_factory.stop_server)
        return self.transport_factory.get_url()

    def test_updating_errors(self):
        base = self.setup_memory()
        t = get_transport(base)
        t = t.clone('path')
        t.create_prefix()
        root = t.base + 'myname'
        ui, cmd = self.get_test_ui_and_cmd((root,))
        mirror = mirrorset.initialise(t, 'myname', t, UI())
        self.assertEqual(3, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('error', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1],
            MatchesException(ValueError('Changeset already open')))

    def test_not_updating_starts(self):
        base = self.setup_memory()
        root = base + 'path/myname'
        t = get_transport(base)
        t = t.clone('path')
        t.create_prefix()
        ui, cmd = self.get_test_ui_and_cmd((root,))
        mirror = mirrorset.initialise(t, 'myname', t, ui)
        mirror.finish_change()
        self.assertEqual(0, cmd.execute())
        t = t.clone('.lmirror/metadata/myname')
        self.assertThat(t.get_bytes('metadata.conf'), DocTestMatches("""[metadata]
basis = 0
latest = 1
timestamp = ...
updating = True

""", ELLIPSIS))
