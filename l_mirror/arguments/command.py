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

"""An Argument that looks up a command object."""

__all__ = ['CommandArgument']

from l_mirror.arguments import AbstractArgument
from l_mirror import commands


class CustomError(ValueError):

    def __str__(self):
        return self.args[0]


class CommandArgument(AbstractArgument):
    """An argument that looks up a command."""

    def _parse_one(self, arg):
        try:
            return commands._find_command(arg)
        except KeyError:
            raise CustomError("Could not find command '%s'." % arg)
