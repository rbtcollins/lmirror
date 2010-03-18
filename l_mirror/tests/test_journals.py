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

"""Tests for the journals module."""

from doctest import ELLIPSIS
import time

from bzrlib.transport import get_transport
from bzrlib.transport.memory import MemoryServer

from testtools.matchers import DocTestMatches

from l_mirror import journals
from l_mirror.ui.model import UI
from l_mirror.tests import ResourcedTestCase


class TestCombiner(ResourcedTestCase):

    def test_init(self):
        combiner = journals.Combiner()

    def test_add_journal_no_conflict(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new', ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j1)

    def test_add_delete_no_conflict(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'del', ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j1)

    def test_add_replace_no_path_no_conflict(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', 'abcdef0123412312341234123412341234123412', 34)))
        combiner.add(j1)

    def test_add_new_new_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new', ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j1)
        self.assertRaises(ValueError, combiner.add, j1)

    def test_add_new_delete_mismatch_path_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new',
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'del',
            ('file', 'abc39d6dd9a7e27622301e935b6eefc78846802e', 11))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_new_delete_no_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new',
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'del',
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j2)
        self.assertEqual({}, combiner.journal.paths)

    def test_add_new_replace_mismatch_path_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new',
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'replace', (
            ('file', 'abc39d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', 'abcdef0123412312341234123412341234123412', 34)))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_new_replace_no_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new',
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'replace', (
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', 'abcdef0123412312341234123412341234123412', 34)))
        combiner.add(j2)
        self.assertEqual({'abc': ('new', 
            ('file', 'abcdef0123412312341234123412341234123412', 34))},
            combiner.journal.paths)

    def test_add_replace_del_no_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', 'abcdef0123412312341234123412341234123412', 34)))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'del',
            ('file', 'abcdef0123412312341234123412341234123412', 34))
        combiner.add(j2)
        self.assertEqual({'abc': ('del', 
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))},
            combiner.journal.paths)

    def test_add_replace_del_mismatch_path_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', 'abcdef0123412312341234123412341234123412', 34)))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'del',
            ('file', '12339d6dd9a7e27622301e935b6eefc78846802e', 34))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_replace_new_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', 'abcdef0123412312341234123412341234123412', 34)))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'new',
            ('file', 'abcdef0123412312341234123412341234123412', 34))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_replace_replace_no_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', 'abcdef0123412312341234123412341234123412', 34)))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'replace', (
            ('file', 'abcdef0123412312341234123412341234123412', 34),
            ('file', '9999999999999999999999999999999999999999', 15)))
        combiner.add(j2)
        self.assertEqual({'abc': ('replace', (
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', '9999999999999999999999999999999999999999', 15)))},
            combiner.journal.paths)

    def test_add_replace_replace_mismatch_path_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', 'abcdef0123412312341234123412341234123412', 34)))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'replace', (
            ('file', 'abc39d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', 'abcdef0123412312341234123412341234123412', 34)))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_del_del_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'del', ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j1)
        self.assertRaises(ValueError, combiner.add, j1)

    def test_add_del_replace_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'del', ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'replace', (
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11)))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_del_new_ok(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'del', ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'new', ('file', '00039d6dd9a7e27622301e935b6eefc78846802e', 34))
        combiner.add(j2)

    def test_as_tree_empty(self):
        combiner = journals.Combiner()
        self.assertEqual({}, combiner.as_tree())

    def test_as_tree_demo(self):
        combiner = journals.Combiner()
        file1 = ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11)
        file2 = ('file', 'abcdef0123412312341234123412341234123412', 34)
        link1 = ('symlink', 'foo bar/baz')
        dir1 = ('dir',)
        expected = {'foo': file1,
                    'bar': {
                        'gam': file2,
                        'quux': link1,
                    },
                    'gam': {
                    }
            }
        j1 = journals.Journal()
        j1.add('foo', 'new', file1)
        j1.add('gam', 'new', dir1)
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('bar', 'new', dir1)
        j2.add('bar/gam', 'new', file1)
        combiner.add(j2)
        j3 = journals.Journal()
        j3.add('bar/gam', 'replace', (file1, file2))
        j3.add('bar/quux', 'new', link1)
        combiner.add(j3)
        self.assertEqual(expected, combiner.as_tree())

    def test_as_tree_replace_fail(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('foo', 'replace', (('dir',), ('dir',)))
        combiner.add(j1)
        self.assertRaises(ValueError, combiner.as_tree)

    def test_as_tree_del_fail(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('foo', 'del', ('dir',))
        combiner.add(j1)
        self.assertRaises(ValueError, combiner.as_tree)

    def test_missing_parent_fail(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('foo/bar', 'new', ('dir',))
        combiner.add(j1)
        self.assertRaises(ValueError, combiner.as_tree)


class TestJournal(ResourcedTestCase):

    def test_add_new_ok(self):
        j1 = journals.Journal()
        j1.add('abc', 'new', ('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        self.assertTrue('abc' in j1.paths)

    def test_add_dup_path_error(self):
        j1 = journals.Journal()
        j1.add('abc', 'new', ('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        self.assertRaises(ValueError, j1.add, 'abc', 'new', ('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11))

    def test_del_new_ok(self):
        j1 = journals.Journal()
        j1.add('abc', 'del', ('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        self.assertTrue('abc' in j1.paths)

    def test_del_dup_path_error(self):
        j1 = journals.Journal()
        j1.add('abc', 'del', ('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        self.assertRaises(ValueError, j1.add, 'abc', 'del', ('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11))

    def test_replace_new_ok(self):
        j1 = journals.Journal()
        j1.add('abc', 'replace', (('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11), ('file',
            'e935b6eefc78846802e12039d6dd9a7e27622301', 12)))
        self.assertTrue('abc' in j1.paths)

    def test_replace_dup_path_error(self):
        j1 = journals.Journal()
        j1.add('abc', 'replace', (('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11), ('file',
            'e935b6eefc78846802e12039d6dd9a7e27622301', 12)))
        self.assertRaises(ValueError, j1.add, 'abc', 'replace', (('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11), ('file',
            'e935b6eefc78846802e12039d6dd9a7e27622301', 12)))

    def test_replace_single_details_errors(self):
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11),
            ('file', 'abcdef1231231231231231231241231231231241', 12)))

    def test_as_bytes(self):
        # as bytes can serialise all types, and is sorted by path.
        j1 = journals.Journal()
        j1.add('abc', 'new', ('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        j1.add('abc/def', 'del', ('dir',))
        j1.add('1234', 'replace', (('symlink', 'foo bar/baz'), ('file', 'e935b6eefc78846802e12039d6dd9a7e27622301', 0)))
        self.assertEqual("""l-mirror-journal-1
1234\0replace\0symlink\0foo bar/baz\0file\0e935b6eefc78846802e12039d6dd9a7e27622301\0000\x00abc\0new\0file\00012039d6dd9a7e27622301e935b6eefc78846802e\00011\0abc/def\0del\0dir""", j1.as_bytes())


class TestParser(ResourcedTestCase):

    def test_parse_demo(self):
        journal = journals.parse("""l-mirror-journal-1
1234\0replace\0symlink\0foo bar/baz\0file\0e935b6eefc78846802e12039d6dd9a7e27622301\0000\x00abc\0new\0file\00012039d6dd9a7e27622301e935b6eefc78846802e\00011\0abc/def\0del\0dir""")
        expected = journals.Journal()
        expected.add('abc', 'new', ('file',
            '12039d6dd9a7e27622301e935b6eefc78846802e', 11))
        expected.add('abc/def', 'del', ('dir',))
        expected.add('1234', 'replace', (('symlink', 'foo bar/baz'), ('file', 'e935b6eefc78846802e12039d6dd9a7e27622301', 0)))
        self.assertEqual(expected.paths, journal.paths)

    def test_parse_empty(self):
        journal = journals.parse('l-mirror-journal-1\n')
        self.assertEqual({}, journal.paths)

    def test_parse_wrong_header(self):
        self.assertRaises(ValueError, journals.parse, 'l-mirror-journal-1')
        self.assertRaises(ValueError, journals.parse, 'l-mirror-journal-2\n')


class TestDiskUpdater(ResourcedTestCase):

    def get_test_ui(self):
        ui = UI()
        return ui

    def setup_memory(self):
        """Create a memory url server and return its url."""
        # XXX: integrate with ui.here better.
        self.transport_factory = MemoryServer()
        self.transport_factory.start_server()
        self.addCleanup(self.transport_factory.stop_server)
        return self.transport_factory.get_url()

    def test_update_demo(self):
        ui = self.get_test_ui()
        now = time.time()
        four_seconds = now - 4
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        basedir.create_prefix()
        basedir.mkdir('dir1')
        basedir.mkdir('dir2')
        basedir.put_bytes('abc', '1234567890\n')
        basedir.put_bytes('dir1/def', 'abcdef')
        last_timestamp = 0 # get everything
        updater = journals.DiskUpdater({}, basedir, last_timestamp, ui)
        journal = updater.finished()
        expected = {
            'dir2': ('new', ('dir',)),
            'dir1': ('new', ('dir',)),
            'abc': ('new', ('file', '12039d6dd9a7e27622301e935b6eefc78846802e', 11)),
            'dir1/def': ('new', ('file', '1f8ac10f23c5b5bc1167bda84b833e5c057a77d2', 6))
            }
        self.assertEqual(expected, journal.paths)
