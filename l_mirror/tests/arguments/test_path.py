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

"""Tests for the path argument type."""

from bzrlib import transport
from l_mirror.arguments import path
from l_mirror.tests import ResourcedTestCase


class TestArgument(ResourcedTestCase):

    def test_parses_as_transport(self):
        arg = path.PathArgument('name')
        result = arg.parse(['load'])
        self.assertEqual([transport.get_transport('load').base], [result[0].base])
        self.assertEqual(1, len(result))

    def test_NotLocal_raises_ValueError(self):
        arg = path.PathArgument('name')
        self.assertRaises(ValueError, arg.parse, ['http://foo/'])
