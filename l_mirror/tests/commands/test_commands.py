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

"""Tests for the commands command."""

from l_mirror.commands import commands
from l_mirror.ui.model import UI
from l_mirror.tests import ResourcedTestCase


class TestCommandCommands(ResourcedTestCase):

    def get_test_ui_and_cmd(self):
        ui = UI()
        cmd = commands.commands(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_shows_a_table_of_commands(self):
        ui, cmd = self.get_test_ui_and_cmd()
        cmd.execute()
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('table', ui.outputs[0][0])
        self.assertEqual(('command', 'description'), ui.outputs[0][1][0])
        command_names = [row[0] for row in ui.outputs[0][1]]
        summaries = [row[1] for row in ui.outputs[0][1]]
        self.assertTrue('help' in command_names)
        self.assertTrue(
            'Get help on a command.' in summaries)
