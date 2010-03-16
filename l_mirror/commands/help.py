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

"""Get help on a command."""

from l_mirror.arguments import command
from l_mirror.commands import Command

class help(Command):
    """Get help on a command."""

    args = [command.CommandArgument('command_name', min=0)]

    def run(self):
        if not self.ui.arguments['command_name']:
            help = """lmirror -- large scale mirroring 
https://launchpad.net/l_mirror/

lmirror commands -- list commands
lmirror help [command] -- help system
"""
        else:
            cmd = self.ui.arguments['command_name'][0]
            help = cmd.__doc__
        self.ui.output_rest(help)
        return 0
