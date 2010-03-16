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

"""Tests for matchers used by or for testing l_mirror."""

import sys

from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.matchers import MatchesException


class TestMatchesException(ResourcedTestCase):

    def test_does_not_match_different_exception_class(self):
        matcher = MatchesException(ValueError("foo"))
        try:
            raise Exception("foo")
        except Exception:
            error = sys.exc_info()
        mismatch = matcher.match(error)
        self.assertNotEqual(None, mismatch)
        self.assertEqual(
            "<type 'exceptions.Exception'> is not a "
            "<type 'exceptions.ValueError'>",
            mismatch.describe())

    def test_does_not_match_different_args(self):
        matcher = MatchesException(Exception("foo"))
        try:
            raise Exception("bar")
        except Exception:
            error = sys.exc_info()
        mismatch = matcher.match(error)
        self.assertNotEqual(None, mismatch)
        self.assertEqual(
            "Exception('bar',) has different arguments to Exception('foo',).",
            mismatch.describe())

    def test_matches_same_args(self):
        matcher = MatchesException(Exception("foo"))
        try:
            raise Exception("foo")
        except Exception:
            error = sys.exc_info()
        mismatch = matcher.match(error)
        self.assertEqual(None, mismatch)
