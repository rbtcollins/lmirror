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
        j1.add('abc', 'new', journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j1)

    def test_add_delete_no_conflict(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'del', journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j1)

    def test_add_replace_no_path_no_conflict(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None)))
        combiner.add(j1)

    def test_add_new_new_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new', journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j1)
        self.assertRaises(ValueError, combiner.add, j1)

    def test_add_new_delete_mismatch_path_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'del',
            journals.FileContent('abc39d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_new_delete_no_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'del',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j2)
        self.assertEqual({}, combiner.journal.paths)

    def test_add_new_replace_mismatch_path_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'replace', (
            journals.FileContent('abc39d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None)))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_new_replace_no_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'new',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None)))
        combiner.add(j2)
        self.assertEqual({'abc': ('new', 
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None))},
            combiner.journal.paths)

    def test_add_replace_del_no_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None)))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'del',
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None))
        combiner.add(j2)
        self.assertEqual({'abc': ('del', 
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))},
            combiner.journal.paths)

    def test_add_replace_del_mismatch_path_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None)))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'del',
            journals.FileContent('12339d6dd9a7e27622301e935b6eefc78846802e', 34, None))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_replace_new_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None)))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'new',
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_replace_replace_no_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None)))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'replace', (
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None),
            journals.FileContent('9999999999999999999999999999999999999999', 15, None)))
        combiner.add(j2)
        self.assertEqual({'abc': ('replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('9999999999999999999999999999999999999999', 15, None)))},
            combiner.journal.paths)

    def test_add_replace_replace_mismatch_path_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None)))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'replace', (
            journals.FileContent('abc39d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('abcdef0123412312341234123412341234123412', 34, None)))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_del_del_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'del', journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j1)
        self.assertRaises(ValueError, combiner.add, j1)

    def test_add_del_replace_conflicts(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'del', journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None)))
        self.assertRaises(ValueError, combiner.add, j2)

    def test_add_del_new_ok(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('abc', 'del', journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        combiner.add(j1)
        j2 = journals.Journal()
        j2.add('abc', 'new', journals.FileContent('00039d6dd9a7e27622301e935b6eefc78846802e', 34, None))
        combiner.add(j2)

    def test_as_tree_empty(self):
        combiner = journals.Combiner()
        self.assertEqual({}, combiner.as_tree())

    def test_as_tree_demo(self):
        combiner = journals.Combiner()
        file1 = journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None)
        file2 = journals.FileContent('abcdef0123412312341234123412341234123412', 34, None)
        link1 = journals.SymlinkContent('foo bar/baz')
        dir1 = journals.DirContent()
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
        j1.add('foo', 'replace', (journals.DirContent(), journals.DirContent()))
        combiner.add(j1)
        self.assertRaises(ValueError, combiner.as_tree)

    def test_as_tree_del_fail(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('foo', 'del', journals.DirContent())
        combiner.add(j1)
        self.assertRaises(ValueError, combiner.as_tree)

    def test_missing_parent_fail(self):
        combiner = journals.Combiner()
        j1 = journals.Journal()
        j1.add('foo/bar', 'new', journals.DirContent())
        combiner.add(j1)
        self.assertRaises(ValueError, combiner.as_tree)


class TestJournal(ResourcedTestCase):

    def test_add_new_ok(self):
        j1 = journals.Journal()
        j1.add('abc', 'new',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        self.assertTrue('abc' in j1.paths)

    def test_add_dup_path_error(self):
        j1 = journals.Journal()
        j1.add('abc', 'new',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        self.assertRaises(ValueError, j1.add, 'abc', 'new',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))

    def test_del_new_ok(self):
        j1 = journals.Journal()
        j1.add('abc', 'del',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        self.assertTrue('abc' in j1.paths)

    def test_del_dup_path_error(self):
        j1 = journals.Journal()
        j1.add('abc', 'del',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        self.assertRaises(ValueError, j1.add, 'abc', 'del',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))

    def test_replace_new_ok(self):
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('e935b6eefc78846802e12039d6dd9a7e27622301', 12, None)))
        self.assertTrue('abc' in j1.paths)

    def test_replace_dup_path_error(self):
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('e935b6eefc78846802e12039d6dd9a7e27622301', 12, None)))
        self.assertRaises(ValueError, j1.add, 'abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('e935b6eefc78846802e12039d6dd9a7e27622301', 12, None)))

    def test_replace_single_details_errors(self):
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None),
            journals.FileContent('abcdef1231231231231231231241231231231241', 12, None)))

    def test_as_bytes(self):
        # as bytes can serialise all types, and is sorted by path.
        j1 = journals.Journal()
        j1.add('abc', 'new',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, 0.0))
        j1.add('abc/def', 'del', journals.DirContent())
        j1.add('1234', 'replace', (
            journals.SymlinkContent('foo bar/baz'),
            journals.FileContent('e935b6eefc78846802e12039d6dd9a7e27622301', 0, 1.5)))
        self.assertEqual("""l-mirror-journal-2
1234\0replace\0symlink\0foo bar/baz\0file\0e935b6eefc78846802e12039d6dd9a7e27622301\0000\x001.500000\x00abc\0new\0file\00012039d6dd9a7e27622301e935b6eefc78846802e\00011\x000.000000\x00abc/def\0del\0dir""", j1.as_bytes())


class TestTransportReplay(ResourcedTestCase):

    def test_orders_new_replace_delete(self):
        # new-replace-delete is a sane default order.
        basedir = get_transport('trace+' + self.setup_memory()).clone('path')
        basedir.create_prefix()
        basedir.put_bytes('abc', 'def')
        basedir.put_bytes('bye', 'by')
        sourcedir = basedir.clone('../source')
        sourcedir.create_prefix()
        sourcedir.put_bytes('abc', '123412341234')
        sourcedir.put_bytes('new', '12341234')
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 3, None),
            journals.FileContent('5a78babbb162531b3a16c55310a4e7228d68f2e9', 12, None)))
        j1.add('bye', 'del', journals.FileContent('d', 2, None))
        j1.add('new', 'new', journals.FileContent('c129b324aee662b04eccf68babba85851346dff9', 8, None))
        del basedir._activity[:]
        ui = UI()
        generator = journals.ReplayGenerator(j1, sourcedir, ui)
        replay = journals.TransportReplay(j1, generator, basedir, ui)
        replay.replay()
        self.assertEqual([('get', 'new'), ('rename', 'new.lmirrortemp', 'new'),
            ('get', 'abc'), ('get', 'abc'), ('delete', 'abc'), ('rename',
            'abc.lmirrortemp', 'abc'), ('delete', 'bye')],
            basedir._activity)


class TestReplayGenerator(ResourcedTestCase):

    def test_orders_new_replace_delete(self):
        # new-replace-delete is a sane default order.
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        basedir.put_bytes('abc', 'def')
        basedir.put_bytes('bye', 'by')
        sourcedir = basedir.clone('../source')
        sourcedir.create_prefix()
        sourcedir.put_bytes('abc', '123412341234')
        sourcedir.put_bytes('new', '12341234')
        j1 = journals.Journal()
        j1.add('abc', 'replace', (
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 3, None),
            journals.FileContent('5a78babbb162531b3a16c55310a4e7228d68f2e9', 12, None)))
        j1.add('bye', 'del', journals.FileContent('d', 2, None))
        j1.add('new', 'new',
            journals.FileContent('c129b324aee662b04eccf68babba85851346dff9', 8, None))
        ui = UI()
        stream = journals.ReplayGenerator(j1, sourcedir, ui)
        content = list(stream.as_bytes())
        content = ''.join(content)
        expected = 'new\x00new\x00file\x00c129b324aee662b04eccf68babba85851346dff9\x008\x00None\x0012341234abc\x00replace\x00file\x0012039d6dd9a7e27622301e935b6eefc78846802e\x003\x00None\x00file\x005a78babbb162531b3a16c55310a4e7228d68f2e9\x0012\x00None\x00123412341234bye\x00del\x00file\x00d\x002\x00None\x00'
        self.assertEqual(expected, content)


class TestParser(ResourcedTestCase):

    def test_parse_v1(self):
        journal = journals.parse("""l-mirror-journal-1
1234\0replace\0symlink\0foo bar/baz\0file\0e935b6eefc78846802e12039d6dd9a7e27622301\0000\x00abc\0new\0file\00012039d6dd9a7e27622301e935b6eefc78846802e\00011\0abc/def\0del\0dir""")
        expected = journals.Journal()
        expected.add('abc', 'new',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, None))
        expected.add('abc/def', 'del', journals.DirContent())
        expected.add('1234', 'replace', (
            journals.SymlinkContent('foo bar/baz'),
            journals.FileContent('e935b6eefc78846802e12039d6dd9a7e27622301', 0, None)))
        self.assertEqual(expected.paths, journal.paths)

    def test_parse_v2(self):
        journal = journals.parse("""l-mirror-journal-2
1234\0replace\0symlink\0foo bar/baz\0file\0e935b6eefc78846802e12039d6dd9a7e27622301\0000\x000\x00abc\0new\0file\00012039d6dd9a7e27622301e935b6eefc78846802e\00011\x002\0abc/def\0del\0dir""")
        expected = journals.Journal()
        expected.add('abc', 'new',
            journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, 2.0))
        expected.add('abc/def', 'del', journals.DirContent())
        expected.add('1234', 'replace', (
            journals.SymlinkContent('foo bar/baz'),
            journals.FileContent('e935b6eefc78846802e12039d6dd9a7e27622301', 0, 0.0)))
        self.assertEqual(expected.paths, journal.paths)

    def test_parse_empty(self):
        journal = journals.parse('l-mirror-journal-1\n')
        self.assertEqual({}, journal.paths)

    def test_parse_wrong_header(self):
        self.assertRaises(ValueError, journals.parse, 'l-mirror-journal-1')
        self.assertRaises(ValueError, journals.parse, 'l-mirror-journal-3\n')


class TestDiskUpdater(ResourcedTestCase):

    def get_test_ui(self):
        ui = UI()
        return ui

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
        updater = journals.DiskUpdater({}, basedir, 'name', last_timestamp, ui)
        journal = updater.finished()
        expected = {
            'dir2': ('new', journals.DirContent()),
            'dir1': ('new', journals.DirContent()),
            'abc': ('new', journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, 0)),
            'dir1/def': ('new', journals.FileContent('1f8ac10f23c5b5bc1167bda84b833e5c057a77d2', 6, 0))
            }
        self.assertEqual(expected, journal.paths)

    def test_skips_other_sets(self):
        ui = self.get_test_ui()
        now = time.time()
        four_seconds = now - 4
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        basedir.create_prefix()
        basedir.mkdir('.lmirror')
        basedir.mkdir('.lmirror/sets')
        basedir.mkdir('.lmirror/sets/name')
        basedir.mkdir('.lmirror/sets/othername')
        basedir.put_bytes('.lmirror/sets/name/abc', '1234567890\n')
        basedir.put_bytes('.lmirror/sets/othername/abc', '1234567890\n')
        last_timestamp = 0 # get everything
        updater = journals.DiskUpdater({}, basedir, 'name', last_timestamp, ui)
        journal = updater.finished()
        expected = {
            '.lmirror': ('new', journals.DirContent()),
            '.lmirror/sets': ('new', journals.DirContent()),
            '.lmirror/sets/name': ('new', journals.DirContent()),
            '.lmirror/sets/name/abc': ('new', journals.FileContent('12039d6dd9a7e27622301e935b6eefc78846802e', 11, 0)),
            }
        self.assertEqual(expected, journal.paths)
