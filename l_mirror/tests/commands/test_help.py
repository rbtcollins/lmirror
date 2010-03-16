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

"""Tests for the help command."""

from l_mirror.commands import help, commands
from l_mirror.ui.model import UI
from l_mirror.tests import ResourcedTestCase


class TestCommand(ResourcedTestCase):

    def get_test_ui_and_cmd(self,args=()):
        ui = UI(args=args)
        cmd = help.help(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_shows_rest_of__doc__(self):
        ui, cmd = self.get_test_ui_and_cmd(args=['commands'])
        cmd.execute()
        self.assertEqual([('rest', commands.commands.__doc__)], ui.outputs)

    def test_shows_general_help_with_no_args(self):
        ui, cmd = self.get_test_ui_and_cmd()
        self.assertEqual(0, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('rest', ui.outputs[0][0])
