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

"""Serve one or more sets."""

import time

from bzrlib import urlutils

from l_mirror.arguments import path, url
from l_mirror.commands import Command
from l_mirror import mirrorset
from l_mirror.server import Server

class serve(Command):
    """Serve one or more sets over HTTP.

    When run, will start a web server on a random port and print the port out.

    The special set name 'all' can be used to tell lmirror to find all the sets
    defined at a location.
    """

    args = [url.URLArgument('sets', min=1, max=None),
        ]

    def run(self):
        server = Server(self.ui)
        server.start()
        try:
            try:
                for transport in self.ui.arguments['sets']:
                    base = transport.clone('..')
                    name = base.relpath(transport.base)
                    if name == 'all':
                        names = base.list_dir('.lmirror/sets')
                    else:
                        names = [name]
                    for name in names:
                        mirror = mirrorset.MirrorSet(base, name, self.ui)
                        server.add(mirror)
                while True:
                    time.sleep(10000000)
            except KeyboardInterrupt:
                return 0
        finally:
            server.stop()
        return 0
