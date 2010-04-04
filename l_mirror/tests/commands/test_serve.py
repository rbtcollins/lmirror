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

"""Tests for the serve command."""

from doctest import ELLIPSIS

from bzrlib.transport import get_transport

from testtools.matchers import DocTestMatches

from l_mirror.commands import serve
from l_mirror import mirrorset
from l_mirror.ui.model import UI
from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.logging_resource import LoggingResourceManager
from l_mirror.tests.matchers import MatchesException


class TestCommandServer(ResourcedTestCase):

    resources = [('logging', LoggingResourceManager())]

    def get_test_ui_and_cmd(self, args):
        ui = UI(args=args)
        cmd = serve.serve(ui)
        ui.set_command(cmd)
        return ui, cmd

    # Some tests that would be good to write:
    # - starts a server
    # - outputs the port
