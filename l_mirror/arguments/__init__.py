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

"""'Arguments' for lmirror.

This is a small typed arguments concept - which is perhaps obsoleted by
argparse in Python 2.7, but for l_mirror is an extension used with
optparse.

The code in this module contains the AbstractArgument base class. Individual
argument types are present in e.g. l_mirror.arguments.string.

See l_mirror.commands.Command for usage of Arguments.

Plugins and extensions wanting to add argument types should either define them
internally or install into l_mirror.arguments as somename (perhaps by
extending the l_mirror.arguments __path__ to include a directory
containing their argument types - no __init__ is needed in that directory.)
"""


class AbstractArgument(object):
    """A argument that a command may need.

    Arguments can be converted into a summary for describing the UI to users,
    and provide validator/parsers for the arguments.

    :ivar: The name of the argument. This is used for retrieving the argument
        from UI objects, and for generating the summary.
    """

    def __init__(self, name, min=1, max=1):
        """Create an AbstractArgument.

        While conceptually a separate SequenceArgument could be used, all
        arguments support sequencing to avoid unnecessary boilerplate in user
        code.

        :param name: The name for the argument.
        :param min: The minimum number of occurences permitted.
        :param max: The maximum number of occurences permitted. None for
            unlimited.
        """
        self.name = name
        self.minimum_count = min
        self.maximum_count = max

    def summary(self):
        """Get a regex-like summary of this argument."""
        result = self.name
        if (self.minimum_count == self.maximum_count and
            self.minimum_count == 1):
                return result
        minmax = (self.minimum_count, self.maximum_count)
        if minmax == (0, 1):
            return result + '?'
        if minmax == (1, None):
            return result + '+'
        if minmax == (0, None):
            return result + '*'
        if minmax[1] == None:
            minmax = (minmax[0], '')
        return result + '{%s,%s}' % minmax

    def parse(self, argv):
        """Evaluate arguments in argv.

        Used arguments are removed from argv.

        :param argv: The arguments to parse.
        :return: The parsed results as a list.
        """
        count = 0
        result = []
        while len(argv) > count and (
            count < self.maximum_count or self.maximum_count is None):
            arg = argv[count]
            count += 1
            result.append(self._parse_one(arg))
        if count < self.minimum_count:
            raise ValueError('not enough arguments present in %s' % argv)
        del argv[:count]
        return result

    def _parse_one(self, arg):
        """Parse a single argument.
        
        :param arg: An arg from an argv.
        :result: The parsed argument.
        :raises ValueError: If the arg cannot be parsed/validated.
        """
        raise NotImplementedError(self._parse_one)
