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

"""Initialise a mirror set."""

from bzrlib import urlutils

from l_mirror.arguments import path
from l_mirror.commands import Command
from l_mirror import mirrorset

class init(Command):
    """Initialise a mirror set."""

    args = [path.PathArgument('mirror_set', min=1, max=1),
        path.PathArgument('content_root', min=0)]

    def run(self):
        transport = self.ui.arguments['mirror_set'][0]
        base = transport.clone('..')
        name = base.relpath(transport.base)
        if not self.ui.arguments['content_root']:
            content_root = base
        else:
            content_root = self.ui.arguments['content_root'][0]
        mirror = mirrorset.initialise(base, name, content_root, self.ui)
        mirror.finish_change()
        return 0
