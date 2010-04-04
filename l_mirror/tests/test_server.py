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

"""Tests for the lmirror server."""

from doctest import ELLIPSIS

from bzrlib.transport import get_transport

from testtools.matchers import DocTestMatches

from l_mirror import gpg, mirrorset, server
from l_mirror.ui.model import UI
from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.logging_resource import LoggingResourceManager


class TestServer(ResourcedTestCase):

    resources = [('logging', LoggingResourceManager())]

    def get_test_ui(self):
        ui = UI()
        return ui

    def test_simplest(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        serve = server.Server(self.get_test_ui())
        serve.start(port=0)
        serve.stop()

    def test_open_on_server(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        serve = server.Server(ui)
        serve.start(port=0)
        try:
            source_mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
            serve.add(source_mirror)
            server_transport = get_transport(serve.addresses[0])
            opened_mirror = mirrorset.MirrorSet(server_transport, 'myname', ui)
            self.assertIsInstance(opened_mirror, mirrorset.HTTPMirrorSet)
        finally:
            serve.stop()
