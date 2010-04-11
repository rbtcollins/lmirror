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

"""Mirrorset, the core of l_mirror.

A MirrorSet is a node in a mirror network, and may be a root node if it has no
sources defined.

See the initialise function to create new MirrorSets, and MirrorSet for docs on
working with a MirrorSet.
"""

__all__ = ['initialise', 'MirrorSet']

import ConfigParser
import json
from StringIO import StringIO
import subprocess
import time

from bzrlib import urlutils
from bzrlib.errors import NoSuchFile, NotLocalUrl
from bzrlib.transport import get_transport

from l_mirror import gpg, journals


def initialise(base, name, content_root, ui):
    """Create a mirrorset at transport, called name, mirroring content_root.

    :param base: The directory under which to put the mirror set
        configuration and metadata. A bzrlib.transport.Transport.
    :param name: The name of the mirrorset.
    :param content_root: The root of the content to be mirrored. A
        bzrlib.transport.Transport.
    :param ui: A l_mirror.ui.AbstractUI.
    :return: A MirrorSet object.
    """
    setdir = base.clone('.lmirror/sets/%s' % name)
    ui.output_log(8, 'l_mirror.mirrorset', 'Creating mirrorset %s at %s'
        % (name, base.base))
    setdir.create_prefix()
    # Ideally we'd use O_EXCL|O_CREAT, but trying a manual open is close enough
    # to race-free, as if it does race, they'll both be creating the same
    # content.
    try:
        MirrorSet(base, name, ui)
    except ValueError:
        pass
    else:
        raise ValueError("Already a set %r configured at %s" % (name,
            base.base))
    setdir.put_bytes('format', '1\n')
    content_relative = urlutils.relative_url(base.base, content_root.base[:-1])
    if not content_relative:
        content_relative = '.'
    setdir.put_bytes('set.conf', '[set]\ncontent_root = %s\n' % content_relative)
    metadir = base.clone('.lmirror/metadata/%s' % name)
    metadir.create_prefix()
    metadir.put_bytes('format', '1\n')
    metadir.put_bytes('metadata.conf', '[metadata]\nbasis = 0\nlatest = 0\ntimestamp = 0\nupdating = True\n')
    journaldir = metadir.clone('journals')
    journaldir.create_prefix()
    journaldir.put_bytes('0', journals.Journal().as_bytes())
    return MirrorSet(base, name, ui)


def MirrorSet(base, name, ui):
    """Open a MirrorSet."""
    try:
        format = base.get_bytes('.lmirror/sets/%s/format' % name)
    except NoSuchFile:
        raise ValueError('No set %r - file not found' % name)
    if format == '1\n':
        return _MirrorSet(base, name, ui)
    if format == 'LMirror Smart Server 1':
        return HTTPMirrorSet(base, name, ui)
    raise ValueError('Unrecognised set format %r' % format)


class _MirrorSet(object):
    """A mirrorable directory structure - a set of files to be mirrored.

    This is the primary model object in lmirror, using it one can manage mirror
    definitions, perform syncs etc.

    On disk a MirrorSet consists of configuration data in
    <basedir>/.lmirror/sets/<name>/:
    * format : Marker to allow compatibility.
    * set.conf: The configuration file. This shoud have one section:
      [set]
      content_root=<relpath to root>
    There is also state data in 
    <basedir>/.lmirror/metadata/<name>/:
    * format : Marker to allow compatibility.
    * metadata.conf: The current metadata. This has one section:
      [metadata]
      basis=<id of earliest full journal>
      latest=<id of latest journal>
      timestamp=<timestamp that last journal scan started at; controls what
        files are hashed and what just stated during a scan>
      updating=True|False # if True clients know that the mirror source may
        be out of sync with the metadata, and wait for that to get sorted.

    :ivar base: The base directory.
    :ivar name: The name of the mirror.
    :ivar excludes: () if not loaded from disk, or the exclude regexes to
        apply when scanning for changes.
    :ivar includes: () if not loaded from disk, or the include regexes to
        apply when scanning for changes.
    :ivar filter_programs: () if not loaded from disk, or the list of programs
        and arguments to run and use when scanning for changes in this
        mirrorset.
    :ivar ui: The AbstractUI output is fed to.
    :ivar gpg_strategy: A bzrlib.gpg.GPGStrategy used for doing gpg signatures.
    :ivar gpgv_strategy: A l_mirror.gpg.GPGVStrategy for doing signature
        checking.
    """

    def __init__(self, base, name, ui):
        """Open an existing MirrorSet.

        :param base: A bzrlib.transport.Transport. The base directory where
            the mirror definition can be found.
        :param name: The name of the mirror set.
        :param ui: An l_mirror.ui.AbstractUI.
        """
        self.base = base
        self.name = name
        self.ui = ui
        self.excludes = ()
        self.includes = ()
        self.filter_programs = ()
        self.gpg_strategy = gpg.SimpleGPGStrategy(None)
        try:
            self.gpgv_strategy = gpg.GPGVStrategy(
                self._setdir().local_abspath('lmirror.gpg'), self.ui)
        except NotLocalUrl:
            # won't be able to do gpgv calls.
            self.gpgv_strategy = None

    def finish_change(self):
        """Scan the mirror set for changes and write a new journal entry.

        This will set updating=False and update the timestamp in the metadata.
        """
        metadata = self._get_metadata()
        if metadata.get('metadata', 'updating') != 'True':
            raise ValueError('No changeset open')
        self.ui.output_log(5, 'l_mirror.mirrorset',
            'finishing change of mirror set %s at %s' % 
            (self.name, self.base.base))
        last = float(metadata.get('metadata', 'timestamp'))
        now = time.time()
        basis = int(metadata.get('metadata', 'basis'))
        latest = int(metadata.get('metadata', 'latest'))
        if metadata.has_option('metadata', 'server'):
            server_url = metadata.get('metadata', 'server')
            server_transport = get_transport(server_url)
            try:
                changes_bytes = server_transport.get_bytes('changes/%s' % self.name)
                # TODO: May require URL decoding to match the transport interface.
                changes = sorted(path.encode('utf8') for path in
                    json.loads(changes_bytes))
            except NoSuchFile:
                server_transport = None
                changes = None
        else:
            server_transport = None
            changes = None
        current_state = self._combine_journals(basis, latest)
        filter_callback = self._get_filter_callback()
        try:
            updater = journals.DiskUpdater(current_state,
                self._content_root_dir(), self.name, last, self.ui,
                includes = self.get_includes(), excludes=self.get_excludes(),
                filter_callback=filter_callback, known_changes=changes)
            journal = updater.finished()
            if journal.paths:
                next_id = latest + 1
                journal_bytes = journal.as_bytes()
                journal_dir = self._journaldir()
                journal_dir.put_bytes(str(next_id), journal_bytes)
                if self._is_signed():
                    signature = self.gpg_strategy.sign(journal_bytes)
                    journal_dir.put_bytes("%s.sig" % next_id, signature)
                metadata.set('metadata', 'latest', str(next_id))
                metadata.set('metadata', 'timestamp', str(now))
            else:
                self.ui.output_rest('No changes found in mirrorset.')
            metadata.set('metadata', 'updating', 'False')
            self._set_metadata(metadata)
            if server_transport is not None:
                server_transport.get_bytes('updated/%s' % self.name)
        finally:
            for filter in filter_callback.filters:
                # Signal it should close and wait for it.
                filter.proc.communicate('')

    def get_excludes(self):
        if self.excludes == ():
            self._parse_content_conf()
        return self.excludes

    def get_includes(self):
        if self.includes == ():
            self._parse_content_conf()
        return self.includes

    def _get_filter_callback(self):
        if self.filter_programs == ():
            self._parse_content_conf()
        filters = []
        for program in self.filter_programs:
            proc = self.ui.subprocess_Popen(program, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE)
            filters.append(journals.ProcessFilter(proc, self.ui, program))
        return journals.FilterCombiner(*filters)

    def get_server(self):
        """Get the current server for this node from metadata.conf."""
        metadata = self._get_metadata()
        if not metadata.has_option('metadata', 'server'):
            return None
        return metadata.get('metadata', 'server')

    def _contentdir(self):
        """Return a transport rooted at the content of this mirror set."""
        return self.base

    def _is_signed(self):
        """Return true if the mirrorset is using gpg signatures."""
        return self._setdir().has('lmirror.gpg')

    def start_change(self):
        """Indicate to readers that changes are being made to the mirror.
        
        This simply sets updating=True in the metadata file.
        """
        metadata = self._get_metadata()
        if metadata.get('metadata', 'updating') != 'False':
            raise ValueError('Changeset already open')
        self.ui.output_log(5, 'l_mirror.mirrorset',
            'Marking mirror %s at %s as updating' %
            (self.name, self.base.base))
        metadata.set('metadata', 'updating', 'True')
        self._set_metadata(metadata)

    def cancel_change(self):
        """Cancel a scheduled change - simply unsets updating."""
        metadata = self._get_metadata()
        if metadata.get('metadata', 'updating') != 'True':
            raise ValueError('No changeset open')
        self.ui.output_log(5, 'l_mirror.mirrorset',
            'Marking mirror %s at %s as not updating' %
            (self.name, self.base.base))
        metadata.set('metadata', 'updating', 'False')
        self._set_metadata(metadata)

    def get_generator(self, from_journal, to_journal):
        """Get a ReplayGenerator for some journals.

        Signatures are not checked - the client should be cross checking and
        signature checking.

        :param from_journal: The first journal to include.
        :param to_journal: The last journal to include.
        """
        needed = range(from_journal, to_journal + 1)
        combiner = journals.Combiner()
        journal_dir = self._journaldir()
        for journal_id in needed:
            journal_bytes = journal_dir.get_bytes(str(journal_id))
            journal = journals.parse(journal_bytes)
            combiner.add(journal)
        return journals.ReplayGenerator(combiner.journal, self._contentdir(),
            self.ui)

    def receive(self, another_mirrorset):
        """Perform a receive from another_mirrorset."""
        # XXX: check its a mirror of the same set. UUID or convergence?
        self.ui.output_log(5, 'l_mirror.mirrorset', 
            'Starting transmission from mirror %s at %s to %s at %s' %
            (another_mirrorset.name, another_mirrorset.base.base, self.name,
             self.base.base))
        metadata = self._get_metadata()
        source_meta = another_mirrorset._get_metadata()
        latest = int(metadata.get('metadata', 'latest'))
        source_latest = int(source_meta.get('metadata', 'latest'))
        signed = self._is_signed()       
        # XXX: BASIS: basis handling needed here (and thats when we
        # need non-overlapping syncing.
        if source_latest > latest:
            needed = range(latest + 1, source_latest + 1)
            new_journals = len(needed)
            combiner = journals.Combiner()
            source_journaldir = another_mirrorset._journaldir()
            journal_dir = self._journaldir()
            for journal_id in needed:
                journal_bytes = source_journaldir.get_bytes(str(journal_id))
                if signed:
                    # Copy the sig, check its valid in the current keyring.
                    sig_name = "%s.sig" % journal_id
                    sig_bytes = source_journaldir.get_bytes(sig_name)
                    journal_dir.put_bytes(sig_name, sig_bytes)
                    self.gpgv_strategy.verify(journal_dir, sig_name,
                        journal_bytes)
                journal_dir.put_bytes(str(journal_id), journal_bytes)
                journal = journals.parse(journal_bytes)
                combiner.add(journal)
            changed_paths = len(combiner.journal.paths)
            # If the keyring was changed and we were not signed before, copy
            # the keyring and check that all signed journals validate.
            keyringpath = '.lmirror/sets/%s/lmirror.gpg' % self.name
            if keyringpath in combiner.journal.paths:
                minijournal = journals.Journal()
                minijournal.paths[keyringpath] = combiner.journal.paths[
                    keyringpath]
                generator = journals.ReplayGenerator(minijournal,
                    another_mirrorset._contentdir(), self.ui)
                replayer = journals.TransportReplay(minijournal, generator,
                    self.base, self.ui)
                replayer.replay()
                for journal_id in needed:
                    try:
                        sig_name = "%s.sig" % journal_id
                        sig_bytes = source_journaldir.get_bytes(sig_name)
                        journal_dir.put_bytes(sig_name, sig_bytes)
                    except NoSuchFile:
                        continue
                    self.gpgv_strategy.verify(journal_dir, sig_name,
                        journal_dir.get_bytes(str(journal_id)))
            # Now we have a journal that is GPG checked representing what we
            # want to receive.
            replayer = journals.TransportReplay(combiner.journal,
                another_mirrorset.get_generator(latest + 1, source_latest),
                self.base, self.ui)
            replayer.replay()
            metadata.set('metadata', 'latest', str(source_latest))
            metadata.set('metadata', 'timestamp',
                source_meta.get('metadata', 'timestamp'))
            self._set_metadata(metadata)
        else:
            changed_paths = 0
            new_journals = 0
        self.ui.output_log(5, 'l_mirror.mirrorset', 
            'Received %d path changes in %d journals from mirror %s at '
            ' %s to %s at %s' %
            (changed_paths, new_journals, another_mirrorset.name,
             another_mirrorset.base.base, self.name, self.base.base))

    def _combine_journals(self, start, stop):
        """Combine a number of journals to get a tree model."""
        model = journals.Combiner()
        journaldir = self._journaldir()
        for journal_id in range(start, stop + 1):
            model.add(journals.parse(journaldir.get_bytes(str(journal_id))))
        return model.as_tree()

    def _setdir(self):
        return self.base.clone('.lmirror/sets/%s' % self.name)

    def set_server(self, server):
        """Set a current server in metadata.conf.

        :param server: The server URL to remember.
        """
        metadata = self._get_metadata()
        if server is None:
            metadata.remove_option('metadata', 'server')
        else:
            metadata.set('metadata', 'server', server)
        self._set_metadata(metadata)

    def _parse_content_conf(self):
        t = self._setdir()
        includes = []
        excludes = []
        programs = []
        try:
            file_bytes = t.get_bytes('content.conf')
            for line in file_bytes.split('\n'):
                if not line:
                    continue
                if line.startswith('include '):
                    includes.append(line[8:])
                elif line.startswith('exclude '):
                    excludes.append(line[8:])
                elif line.startswith('program '):
                    programs.append(line[8:])
        except NoSuchFile:
            pass
        self.includes = includes
        self.excludes = excludes
        self.filter_programs = programs

    def content_root_path(self):
        return self._get_settings().get('set', 'content_root')

    def _content_root_dir(self):
        return self.base.clone(self.content_root_path())

    def _metadatadir(self):
        """Get the transport for metadata."""
        return self.base.clone('.lmirror/metadata/%s' % self.name)

    def _journaldir(self):
        """Get the transport for journals."""
        return self._metadatadir().clone('journals')

    def _set_metadata(self, metadata):
        """Update metadata on disk."""
        output = StringIO()
        metadata.write(output)
        self._metadatadir().put_bytes('metadata.conf', output.getvalue())

    def _get_metadata(self):
        """Get a config parser with the metadata contents in it."""
        parser = OrderedConfigParser()
        parser.readfp(self._metadatadir().get('metadata.conf'))
        return parser

    def _get_settings(self):
        """Get a config parser with the set config contents in it."""
        parser = OrderedConfigParser()
        parser.readfp(self._get_settings_file())
        return parser

    def _get_settings_file(self):
        return self._setdir().get('set.conf')


class HTTPMirrorSet(_MirrorSet):
    """Specialised MirrorSet to use an HTTP Smart server."""

    def _metadatadir(self):
        """Get the transport for metadata."""
        return self.base.clone('metadata/%s' % self.name)

    def _contentdir(self):
        """Return a transport rooted at the content of this mirror set."""
        return self.base.clone('content/%s' % self.name)

    def get_generator(self, from_journal, to_journal):
        # Work around https://bugs.edge.launchpad.net/bzr/+bug/555032
        code, stream = self.base._get('stream/%s/%s/%s' % (self.name, from_journal,
            to_journal), None)
        return journals.FromFileGenerator(stream, self.ui)


class OrderedConfigParser(ConfigParser.ConfigParser):
    """Make write() not dictionary-order based."""

    def write(self, fp):
        """Write an .ini-format representation of the configuration state."""
        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT)
            for (key, value) in sorted(self._defaults.items()):
                fp.write("%s = %s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for (key, value) in sorted(self._sections[section].items()):
                if key != "__name__":
                    fp.write("%s = %s\n" %
                             (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
