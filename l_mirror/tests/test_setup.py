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

"""Tests for setup.py."""

import doctest
import os.path
import subprocess

from testtools import (
    TestCase,
    )
from testtools.matchers import (
    DocTestMatches,
    )

class TestCanSetup(TestCase):

    def test_bdist(self):
        # Single smoke test to make sure we can build a package.
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'setup.py')
        proc = subprocess.Popen([path, 'bdist'], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output, _ = proc.communicate()
        self.assertEqual(0, proc.returncode)
        self.assertThat(output, DocTestMatches("""...
...bin/lmirror ...
""", doctest.ELLIPSIS))
