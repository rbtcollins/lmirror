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

from optparse import Option
import time

from bzrlib import urlutils
try:
    import pyinotify
except ImportError:
    pyinotify = None

from l_mirror.arguments import path, url
from l_mirror.commands import Command
from l_mirror import mirrorset
from l_mirror.server import Server, SetWatcher

class serve(Command):
    """Serve one or more sets over HTTP.

    When run, will start a web server on a random port and print the port out.

    The special set name 'all' can be used to tell lmirror to find all the sets
    defined at a location.
    """

    args = [url.URLArgument('sets', min=1, max=None),
        ]
    options = [
        Option("--inotify", dest="inotify", help="Attempt to Monitor the "
            "directory tree that each set contains via inotify. This will "
            "perform a scan of the tree immediately, and after that accrue "
            "changes made within that tree. This causes a lmirror.server "
            "file to be written to the .lmirror/metadata/<set>/ directory "
            "obtaining the URL of the server. This URL is then used by "
            "lmirror finish-change to request a list of candidate changes "
            "to review.", action="store_true", default=False),
        Option("--port", "-p", dest="port", help="Control what port the server "
            "runs on. Use 0 to auto-allocate a port. Defaults to 8080.",
            action="store_true", default=8080),
        ]

    def run(self):
        server = Server(self.ui)
        server.start(self.ui.options.port)
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
                # Server is running, now we add inotify watches for existing
                # content.
                if self.ui.options.inotify:
                    if pyinotify is None:
                        self.ui.output_log(9, __name__, "inotify requested, "
                            "but pyinotify could not be imported.")
                    else:
                        watcher = SetWatcher()
                        server.set_watcher = watcher
                        try:
                            for mirror in server.mirrorsets.values():
                                mirror.set_server(server.addresses[0])
                                watcher.add(mirror)
                            watcher.notifier.loop()
                        finally:
                            for mirror in server.mirrorsets.values():
                                mirror.set_server(None)
                if pyinotify is None or not self.ui.options.inotify:
                    while True:
                        time.sleep(10000000)
            except KeyboardInterrupt:
                return 0
        finally:
            server.stop()
        return 0
