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

from optparse import Option

from bzrlib import urlutils

from l_mirror.arguments import path
from l_mirror.commands import Command
from l_mirror import mirrorset

class init(Command):
    """Initialise a mirror set.
    
    Take the place and name to create the mirror set, and optionally a 
    different directory to replicate. Note that if the directory to
    replicate is the same as the location of the mirror set configuration, then
    config changes will automatically propogate - this is the default if you
    just run (for example)::
    
      $ lmirror init /srv/ubuntu/ubuntu
    
    which will create a mirror set called ubuntu in /srv/ubuntu.

    Creating a mirror set does a scan-and-hash of the entire contents of that
    directory, so it will take time run about the same as tarring up the entire
    directory.
    """

    args = [path.PathArgument('mirror_set', min=1, max=1),
        path.PathArgument('content_root', min=0)]
    options = [Option("--empty", dest="empty", help="Create the new mirror set"
        " as empty. This is useful when you intend to customise and tuen the"
        " filters for it and don't want to wait for an initial scan to take"
        " place.", action="store_true", default=False)
        ]

    def run(self):
        transport = self.ui.arguments['mirror_set'][0]
        base = transport.clone('..')
        name = base.relpath(transport.base)
        if not self.ui.arguments['content_root']:
            content_root = base
        else:
            content_root = self.ui.arguments['content_root'][0]
        mirror = mirrorset.initialise(base, name, content_root, self.ui)
        if not self.ui.options.empty:
            mirror.finish_change()
        return 0
