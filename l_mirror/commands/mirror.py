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

"""Mirror an existing mirror set."""

from bzrlib import urlutils

from l_mirror.arguments import path, url
from l_mirror.commands import Command
from l_mirror import mirrorset

class mirror(Command):
    """Mirror a mirror set.

    Takes the mirror to mirror from, and the mirror to mirror too. If the
    target does not exist it will be populated from the source mirror.
    
    For example:
    
      $ lmirror mirror http://archive.ubuntu.com/ubuntu/ubuntu /srv/ubuntu

    will initialise a mirror set called ubuntu in /srv/ubuntu, with 
    http://archive.ubuntu.com/ubuntu/ as a known sender.
    
    Mirroring will not generally copy content already present, but the first
    mirror run can still take considerable time. Subsequent runs should be
    extremely fast.
    """

    args = [url.URLArgument('source_mirror', min=1, max=1),
        path.PathArgument('target_mirror', min=1, max=1)]

    def run(self):
        source_transport = self.ui.arguments['source_mirror'][0]
        source_base = source_transport.clone('..')
        name = source_base.relpath(source_transport.base)
        target_base = self.ui.arguments['target_mirror'][0]
        source = mirrorset.MirrorSet(source_base, name, self.ui)
        try:
            target = mirrorset.MirrorSet(target_base, name, self.ui)
        except ValueError:
            # No mirror there yet
            target = mirrorset.initialise(target_base, name,
                target_base.clone(source.content_root_path()), self.ui)
            target.cancel_change()
        target.receive(source)
        return 0
