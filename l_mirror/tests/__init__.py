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

"""The l_mirror tests and test only code.

Tests are structured to mirror the main code structure. That is, tests for
a module l_mirror.foo.bar are in a test module l_mirrr.tests.foo.test_bar.
"""

import unittest

from bzrlib.transport.memory import MemoryServer
import testresources
from testscenarios import generate_scenarios
from testtools import TestCase

from l_mirror.tests import memory_transport_stat

class ResourcedTestCase(TestCase, testresources.ResourcedTestCase):
    """Make all l_mirror tests have resource support."""

    def setUp(self):
        TestCase.setUp(self)
        testresources.ResourcedTestCase.setUpResources(self)
        self.addCleanup(testresources.ResourcedTestCase.tearDownResources,
            self)

    def setup_memory(self):
        """Create a memory url server and return its url."""
        # XXX: integrate with ui.here better.
        self.transport_factory = MemoryServer()
        self.transport_factory.start_server()
        self.addCleanup(self.transport_factory.stop_server)
        self.addCleanup(memory_transport_stat.install())
        return self.transport_factory.get_url()


def test_suite():
    packages = [
        'arguments',
        'commands',
        'ui',
        ]
    names = [
        'arguments',
        'commands',
        'journals',
        'logging_resource',
        'logging_support',
        'matchers',
        'mirrorset',
        'monkeypatch',
        'ui',
        'setup',
        'server',
        'stubpackage',
        'stubhome',
        ]
    module_names = ['l_mirror.tests.test_' + name for name in names]
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(module_names)
    result = testresources.OptimisingTestSuite()
    result.addTests(generate_scenarios(suite))
    for pkgname in packages:
        pkg = __import__('l_mirror.tests.' + pkgname, globals(),
            locals(), ['test_suite'])
        result.addTests(generate_scenarios(pkg.test_suite()))
    return result
