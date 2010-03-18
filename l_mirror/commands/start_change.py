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

"""Tell receivers a change is being made to a mirror set."""

from bzrlib import urlutils

from l_mirror.arguments import path
from l_mirror.commands import Command
from l_mirror import mirrorset

class start_change(Command):
    """Start a new change to a mirror set.
    
    This tells receivers that they may not be able to read the file content
    they want as it is being changed - so when a mismatch is detected they
    can handle this differently than a fatal error.

    Typically you would run this before any cron job or the like which may
    either delete or change paths already on disk.
    
    Takes the mirror set to start a change on.
    """

    args = [path.PathArgument('mirror_set', min=1, max=1)]

    def run(self):
        transport = self.ui.arguments['mirror_set'][0]
        base = transport.clone('..')
        name = base.relpath(transport.base)
        mirror = mirrorset.MirrorSet(base, name, self.ui)
        mirror.start_change()
        return 0
