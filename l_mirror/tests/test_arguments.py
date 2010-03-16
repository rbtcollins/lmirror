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

"""Tests for the arguments package."""

from l_mirror import arguments
from l_mirror.tests import ResourcedTestCase


class TestAbstractArgument(ResourcedTestCase):

    def test_init_base(self):
        arg = arguments.AbstractArgument('name')
        self.assertEqual('name', arg.name)
        self.assertEqual('name', arg.summary())

    def test_init_optional(self):
        arg = arguments.AbstractArgument('name', min=0)
        self.assertEqual(0, arg.minimum_count)
        self.assertEqual('name?', arg.summary())

    def test_init_repeating(self):
        arg = arguments.AbstractArgument('name', max=None)
        self.assertEqual(None, arg.maximum_count)
        self.assertEqual('name+', arg.summary())

    def test_init_optional_repeating(self):
        arg = arguments.AbstractArgument('name', min=0, max=None)
        self.assertEqual(None, arg.maximum_count)
        self.assertEqual('name*', arg.summary())

    def test_init_arbitrary(self):
        arg = arguments.AbstractArgument('name', max=2)
        self.assertEqual('name{1,2}', arg.summary())

    def test_init_arbitrary_infinite(self):
        arg = arguments.AbstractArgument('name', min=2, max=None)
        self.assertEqual('name{2,}', arg.summary())

    def test_parsing_calls__parse_one(self):
        calls = []
        class AnArgument(arguments.AbstractArgument):
            def _parse_one(self, arg):
                calls.append(arg)
                return ('1', arg)
        argument = AnArgument('foo', max=2)
        args = ['thing', 'other', 'stranger']
        # results are returned
        self.assertEqual([('1', 'thing'), ('1', 'other')],
            argument.parse(args))
        # used args are removed
        self.assertEqual(['stranger'], args)
        # parse function was used
        self.assertEqual(['thing', 'other'], calls)

    def test_parsing_unlimited(self):
        class AnArgument(arguments.AbstractArgument):
            def _parse_one(self, arg):
                return arg
        argument = AnArgument('foo', max=None)
        args = ['thing', 'other']
        # results are returned
        self.assertEqual(['thing', 'other'], argument.parse(args))
        # used args are removed
        self.assertEqual([], args)

    def test_parsing_too_few(self):
        class AnArgument(arguments.AbstractArgument):
            def _parse_one(self, arg):
                return arg
        argument = AnArgument('foo')
        self.assertRaises(ValueError, argument.parse, [])


# No interface tests for now, because the interface we expect is really just
# _parse_one; however if bugs or issues show up... then we should add them.
