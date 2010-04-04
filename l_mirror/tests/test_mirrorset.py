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

"""Tests for the mirrorset module."""

from doctest import ELLIPSIS

from bzrlib import gpg as bzrgpg
from bzrlib.transport import get_transport

from testtools.matchers import DocTestMatches

from l_mirror import gpg, mirrorset
from l_mirror.ui.model import UI
from l_mirror.tests import ResourcedTestCase


class TestMirrorSet(ResourcedTestCase):

    def get_test_ui(self):
        ui = UI()
        return ui

    def test_create_set(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        t = basedir.clone('.lmirror/sets/myname')
        self.assertEqual('1\n', t.get_bytes('format'))
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = .
"""))
        self.assertEqual(basedir, mirror.base)
        self.assertEqual('myname', mirror.name)
        self.assertEqual(ui, mirror.ui)

    def test_error_creating_existing_set(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        self.assertRaises(ValueError,
            mirrorset.initialise, basedir, 'myname', basedir, ui)

    def test_accepts_content_root(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        contentdir = basedir.clone('../content')
        contentdir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', contentdir, ui)
        t = basedir.clone('.lmirror/sets/myname')
        self.assertEqual('1\n', t.get_bytes('format'))
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = ../content
"""))

    def test_second_set_can_be_created(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        mirror = mirrorset.initialise(basedir, 'myname2', basedir, ui)
        t = basedir.clone('.lmirror/sets/myname2')
        self.assertEqual('1\n', t.get_bytes('format'))
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = .
"""))

    def test_creates_metadata_dir(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        t = basedir.clone('.lmirror/metadata/myname')
        self.assertEqual('1\n', t.get_bytes('format'))
        self.assertThat(t.get_bytes('metadata.conf'), DocTestMatches("""[metadata]
basis = 0
latest = 0
timestamp = 0
updating = True
""", ELLIPSIS))
        self.assertThat(t.get_bytes('journals/0'), DocTestMatches("""l-mirror-journal-2
"""))

    def test_open_set(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirrorset.initialise(basedir, 'myname', basedir, ui)
        t = basedir.clone('.lmirror/sets/myname')
        self.assertEqual('1\n', t.get_bytes('format'))
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = .
"""))   
        mirror = mirrorset.MirrorSet(basedir, 'myname', ui)

    def test_open_missing(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        self.assertRaises(ValueError, mirrorset.MirrorSet, basedir, 'myname', ui)

    def test_open_wrong_format(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirrorset.initialise(basedir, 'myname', basedir, ui)
        t = basedir.clone('.lmirror/sets/myname')
        self.assertEqual('1\n', t.get_bytes('format'))
        t.put_bytes('format', '2\n')
        self.assertThat(t.get_bytes('set.conf'), DocTestMatches("""[set]
content_root = .
"""))   
        self.assertRaises(ValueError, mirrorset.MirrorSet, basedir, 'myname', ui)

    def test_parse_content_conf(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        t = basedir.clone('.lmirror/sets/myname')
        t.put_bytes('content.conf', """include a regex
exclude another regex
# a comment
""")
        mirror._parse_content_conf()
        self.assertEqual(['another regex'], mirror.excludes)
        self.assertEqual(['a regex'], mirror.includes)

    def test_start_change_updating_error(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        self.assertRaises(ValueError, mirror.start_change)

    def test_start_change_not_updating_starts_change(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        mirror.finish_change()
        mirror.start_change()
        # We know finish_change errors if a change isn't open, so it working is
        # sufficient.
        mirror.finish_change()

    def test_finish_change_not_updating_error(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        mirror.finish_change()
        self.assertRaises(ValueError, mirror.finish_change)

    def test_finish_change_no_change_no_new_journal(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        mirror.finish_change()
        mirror.start_change()
        mirror.finish_change()
        self.assertEqual('1', mirror._get_metadata().get('metadata', 'latest'))
        self.assertEqual(('rest', 'No changes found in mirrorset.'),
            ui.outputs[-1])

    def test_finish_change_scans_content(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        basedir.create_prefix()
        basedir.mkdir('dir1')
        basedir.mkdir('dir2')
        basedir.put_bytes('abc', '1234567890\n')
        basedir.put_bytes('dir1/def', 'abcdef')
        mirror.finish_change()
        t = basedir.clone('.lmirror/metadata/myname')
        self.assertThat(t.get_bytes('metadata.conf'), DocTestMatches("""[metadata]
basis = 0
latest = 1
timestamp = ...
updating = False

""", ELLIPSIS))
        self.assertThat(t.get_bytes('journals/1'), DocTestMatches("""l-mirror-journal-2
.lmirror\x00new\x00dir\x00.lmirror/sets\x00new\x00dir\x00.lmirror/sets/myname\x00new\x00dir\x00.lmirror/sets/myname/format\x00new\x00file\x00e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e\x002\x000.000000\x00.lmirror/sets/myname/set.conf\x00new\x00file\x00061df21cf828bb333660621c3743cfc3a3b2bd23\x0023\x000.000000\x00abc\x00new\x00file\x0012039d6dd9a7e27622301e935b6eefc78846802e\x0011\x000.000000\x00dir1\x00new\x00dir\x00dir1/def\x00new\x00file\x001f8ac10f23c5b5bc1167bda84b833e5c057a77d2\x006\x000.000000\x00dir2\x00new\x00dir"""))
    
    def test_include_excludes_honoured(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        basedir.create_prefix()
        basedir.mkdir('dir1')
        basedir.mkdir('dir2')
        basedir.put_bytes('abc', '1234567890\n')
        basedir.put_bytes('dir2/included', '1234567890\n')
        basedir.put_bytes('dir1/def', 'abcdef')
        mirror.includes = ['included']
        mirror.excludes = ['dir2/', 'dir1']
        mirror.finish_change()
        t = basedir.clone('.lmirror/metadata/myname')
        self.assertThat(t.get_bytes('metadata.conf'), DocTestMatches("""[metadata]
basis = 0
latest = 1
timestamp = ...
updating = False

""", ELLIPSIS))
        self.assertThat(t.get_bytes('journals/1'), DocTestMatches("""l-mirror-journal-2
.lmirror\x00new\x00dir\x00.lmirror/sets\x00new\x00dir\x00.lmirror/sets/myname\x00new\x00dir\x00.lmirror/sets/myname/format\x00new\x00file\x00e5fa44f2b31c1fb553b6021e7360d07d5d91ff5e\x002\x000.000000\x00.lmirror/sets/myname/set.conf\x00new\x00file\x00061df21cf828bb333660621c3743cfc3a3b2bd23\x0023\x000.000000\x00abc\x00new\x00file\x0012039d6dd9a7e27622301e935b6eefc78846802e\x0011\x000.000000\x00dir2\x00new\x00dir\x00dir2/included\x00new\x00file\x0012039d6dd9a7e27622301e935b6eefc78846802e\x0011\x000.000000"""))
    
    def test_signs_when_there_is_a_keyring(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        mirror.gpg_strategy = bzrgpg.LoopbackGPGStrategy(None)
        t = basedir.clone('.lmirror/sets/myname')
        t.put_bytes('lmirror.gpg', '')
        mirror.finish_change()
        metadatadir = mirror._metadatadir()
        self.assertEqual(
            "-----BEGIN PSEUDO-SIGNED CONTENT-----\n" +
            metadatadir.get_bytes('journals/1') +
            "-----END PSEUDO-SIGNED CONTENT-----\n",
            metadatadir.get_bytes('journals/1.sig'))

    def test_receive_replays_and_updates_metadata(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        # two journals exist from this simple operation - 0 and 1, but 
        # need 3, as new clones start with 0
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        basedir.create_prefix()
        basedir.mkdir('dir1')
        basedir.mkdir('dir2')
        basedir.put_bytes('abc', '1234567890\n')
        basedir.put_bytes('dir1/def', 'abcdef')
        mirror.finish_change()
        mirror.start_change()
        basedir.put_bytes('dada', '123456789a\n')
        mirror.finish_change()
        clonedir = basedir.clone('../clone')
        clonedir.create_prefix()
        clone = mirrorset.initialise(clonedir, 'myname', clonedir, ui)
        clone.cancel_change()
        clone.receive(mirror)
        mirrormeta = mirror._get_metadata()
        metadata = clone._get_metadata()
        self.assertEqual('2', metadata.get('metadata', 'latest'))
        self.assertEqual(
            mirrormeta.get('metadata', 'timestamp'),
            metadata.get('metadata', 'timestamp'))
        # check we got a file from each journal
        self.assertEqual('123456789a\n', clonedir.get_bytes('dada'))
        self.assertEqual('1234567890\n', clonedir.get_bytes('abc'))
        # And the journals should be identical.
        mirrorjournal = mirror._journaldir()
        clonejournal = clone._journaldir()
        self.assertEqual(mirrorjournal.get_bytes('1'), clonejournal.get_bytes('1'))
        self.assertEqual(mirrorjournal.get_bytes('2'), clonejournal.get_bytes('2'))

    def test_checks_when_there_is_a_keyring(self):
        basedir = get_transport(self.setup_memory()).clone('path')
        basedir.create_prefix()
        ui = self.get_test_ui()
        mirror = mirrorset.initialise(basedir, 'myname', basedir, ui)
        mirror.gpg_strategy = bzrgpg.LoopbackGPGStrategy(None)
        t = basedir.clone('.lmirror/sets/myname')
        t.put_bytes('lmirror.gpg', '')
        mirror.finish_change()
        metadatadir = mirror._metadatadir()
        self.assertEqual(
            "-----BEGIN PSEUDO-SIGNED CONTENT-----\n" +
            metadatadir.get_bytes('journals/1') +
            "-----END PSEUDO-SIGNED CONTENT-----\n",
            metadatadir.get_bytes('journals/1.sig'))
        clonedir = basedir.clone('../clone')
        clonedir.create_prefix()
        clone = mirrorset.initialise(clonedir, 'myname', clonedir, ui)
        clone.cancel_change()
        clone.gpgv_strategy = gpg.TestGPGVStrategy([metadatadir.get_bytes('journals/1')])
        clone.receive(mirror)
        metadata = clone._get_metadata()
        self.assertEqual('1', metadata.get('metadata', 'latest'))
        self.assertEqual(
            "-----BEGIN PSEUDO-SIGNED CONTENT-----\n" +
            metadatadir.get_bytes('journals/1') +
            "-----END PSEUDO-SIGNED CONTENT-----\n",
            clone._metadatadir().get_bytes('journals/1.sig'))
