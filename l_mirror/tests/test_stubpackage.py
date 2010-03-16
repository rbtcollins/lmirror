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

"""Tests for the stubpackage test helper."""

import os.path

from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.stubpackage import (
    StubPackageResource,
    TempDirResource,
    )


class TestStubPackageResource(ResourcedTestCase):

    def test_has_tempdir(self):
        resource = StubPackageResource('foo', [])
        self.assertEqual(1, len(resource.resources))
        self.assertIsInstance(resource.resources[0][1], TempDirResource)

    def test_writes_package(self):
        resource = StubPackageResource('foo', [('bar.py', 'woo')])
        pkg = resource.getResource()
        self.addCleanup(resource.finishedWith, pkg)
        self.assertEqual('', file(os.path.join(pkg.base, 'foo',
            '__init__.py')).read())
        self.assertEqual('woo', file(os.path.join(pkg.base, 'foo',
            'bar.py')).read())

    def test_no__init__(self):
        resource = StubPackageResource('foo', [('bar.py', 'woo')], init=False)
        pkg = resource.getResource()
        self.addCleanup(resource.finishedWith, pkg)
        self.assertFalse(os.path.exists(os.path.join(pkg.base, 'foo',
            '__init__.py')))


class TestTempDirResource(ResourcedTestCase):
    """Tests for the StubPackage resource."""

    def test_makes_a_dir(self):
        resource = TempDirResource()
        tempdir = resource.getResource()
        try:
            self.assertTrue(os.path.exists(tempdir))
        finally:
            resource.finishedWith(tempdir)
        self.assertFalse(os.path.exists(tempdir))
