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

"""testtools.matchers.Matcher style matchers to help test l_mirror."""

from testtools.matchers import Matcher, Mismatch

__all__ = ['MatchesException']


class MatchesException(Matcher):
    """Match an exc_info tuple against an exception."""

    def __init__(self, exception):
        """Create a MatchesException that will match exc_info's for exception.
        
        :param exception: An exception to check against an exc_info tuple. The
            traceback object is not inspected, only the type and arguments of
            the exception.
        """
        Matcher.__init__(self)
        self.expected = exception

    def match(self, other):
        if type(other) != tuple:
            return _StringMismatch('%r is not an exc_info tuple' % other)
        if not issubclass(other[0], type(self.expected)):
            return _StringMismatch('%r is not a %r' % (
                other[0], type(self.expected)))
        if other[1].args != self.expected.args:
            return _StringMismatch('%r has different arguments to %r.' % (
                other[1], self.expected))

    def __str__(self):
        return "MatchesException(%r)" % self.expected


class _StringMismatch(Mismatch):
    """Convenience mismatch for simply-calculated string descriptions."""

    def __init__(self, description):
        self.description = description

    def describe(self):
        return self.description
