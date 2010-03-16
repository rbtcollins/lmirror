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

"""Tests for the monkeypatch helper."""

from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.monkeypatch import monkeypatch

reference = 23

class TestMonkeyPatch(ResourcedTestCase):

    def test_patch_and_restore(self):
        cleanup = monkeypatch(
            'l_mirror.tests.test_monkeypatch.reference', 45)
        self.assertEqual(45, reference)
        cleanup()
        self.assertEqual(23, reference)
