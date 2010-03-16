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

"""Tests for the command argument."""

from l_mirror.arguments import command
from l_mirror.commands import commands
from l_mirror.tests import ResourcedTestCase


class TestArgument(ResourcedTestCase):

    def test_looks_up_command(self):
        arg = command.CommandArgument('name')
        result = arg.parse(['commands'])
        self.assertEqual([commands.commands], result)

    def test_no_command(self):
        arg = command.CommandArgument('name')
        err = self.assertRaises(ValueError, arg.parse, ['one'])
        self.assertEqual("Could not find command 'one'.", str(err))

