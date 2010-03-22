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

"""Tests for the logging isolation resource."""

import logging

from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.logging_resource import LoggingResourceManager


class TestLoggingResource(ResourcedTestCase):

    def assertLoggingManagerAndRootConnected(self):
        self.assertEqual(logging.Logger.root, logging.root)
        self.assertIsInstance(logging.Logger.manager, logging.Manager)
        self.assertEqual(logging.Logger.manager.root, logging.Logger.root)

    def test_make_nukes_config(self):
        mgr = LoggingResourceManager()
        res = mgr.make({})
        self.addCleanup(mgr.clean, res)
        self.assertIsInstance(logging.root, logging.RootLogger)
        self.assertLoggingManagerAndRootConnected()

    def test_clean_restores_config(self):
        old = logging.root
        mgr = LoggingResourceManager()
        res = mgr.make({})
        mgr.clean(res)
        self.assertEqual(old, logging.root)
        self.assertLoggingManagerAndRootConnected()

    def test_always_dirty(self):
        mgr = LoggingResourceManager()
        self.assertTrue(mgr.isDirty())
        self.assertTrue(mgr._dirty)
