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

"""Journals are the individual items that l_mirror uses to synchronise changes.

When a mirror set is updated a new journal is written (see DiskUpdater for
instance), and when a node is receiving updates it receives all the journals it
is missing, and then the updates determined by combining all the journals
together.

The parse() function can parse a journal bytes to make a new Journal object.

The Combiner object can combine multiple journals together, and then either
generate the model of a tree on disk, or a new journal with redundant changes
eliminated.

DiskUpdater is a class to compare a memory 'tree' and a bzr transport and 
output a journal to update the tree to match the transport.

Various Replay objects can replay a journal. TransportReplay replays a journal
by reading the file content from a transport object.
"""

__all__ = ['parse', 'Combiner', 'Journal', 'DiskUpdater', 'TransportReplay']

import errno
import os
from hashlib import sha1 as sha
import re

from bzrlib import errors, osutils


class Combiner(object):
    """Combine multiple journals.
    
    :ivar journal: The combined journal that is being created.
    """

    def __init__(self):
        """Create a Combiner object."""
        self.journal = Journal()

    def add(self, journal):
        """Add journal to the combined journal.

        :raises ValueError: If the journal cannot be safely combined.
        """
        # paths to delete after iteration.
        pending_del_paths = []
        merged_content = {}
        for path, new_content in journal.paths.iteritems():
            old_content = self.journal.paths.get(path, None)
            if old_content is None:
                continue
            # resolve here
            old_action = old_content[0]
            new_action = new_content[0]
            if (old_action, new_action) == ('new', 'new'):
                raise ValueError('Attempt to add %r twice.' % path)
            elif (old_action, new_action) == ('new', 'del'):
                if old_content[1] != new_content[1]:
                    raise ValueError('Attempt to delete wrong content %r, %r' %
                        (old_content, new_content))
                pending_del_paths.append(path)
            elif (old_action, new_action) == ('new', 'replace'):
                if old_content[1] != new_content[1][0]:
                    raise ValueError('Attempt to replace wrong content %r, %r' %
                        (old_content, new_content))
                merged_content[path] = ('new', new_content[1][1])
            elif (old_action, new_action) == ('del', 'new'):
                merged_content[path] = ('replace', (old_content[1], new_content[1]))
            elif (old_action, new_action) == ('del', 'del'):
                raise ValueError('Attempt to delete %r twice.' % path)
            elif (old_action, new_action) == ('del', 'replace'):
                raise ValueError('Attempt to replace deleted path %r.' % path)
            elif (old_action, new_action) == ('replace', 'new'):
                raise ValueError('Attempt to add %r twice.' % path)
            elif (old_action, new_action) == ('replace', 'del'):
                if old_content[1][1] != new_content[1]:
                    raise ValueError('Attempt to delete wrong content %r, %r' %
                        (old_content, new_content))
                merged_content[path] = ('del', old_content[1][0])
            elif (old_action, new_action) == ('replace', 'replace'):
                if old_content[1][1] != new_content[1][0]:
                    raise ValueError('Attempt to replace wrong content %r, %r' %
                        (old_content, new_content))
                merged_content[path] = ('replace', (old_content[1][0], new_content[1][1]))
            else:
                raise ValueError("Unknown action pair %r" % (
                    (old_action, new_action),))
        # backdoor for speed - XXX may be premature. 
        self.journal.paths.update(journal.paths)
        self.journal.paths.update(merged_content)
        for path in pending_del_paths:
            del self.journal.paths[path]

    def as_tree(self):
        """Convert a from-null combined journal into a tree.

        The tree is represented as a simple dict (path -> content) where content
        is either another dict, for directories, or the kind_data for the path.
        
        :return: A dict representing the tree that the journal would create if
            replayed.
        :raises ValueError: If the journal contains any delete, replace actions
            or items with missing parents.
        """
        result = {}
        for path, (action, kind_data) in sorted(self.journal.paths.iteritems()):
            if action in ('del', 'replace'):
                raise ValueError(
                    'cannot generate a tree representation for a partial '
                    ' journal, path %r is not new.' % path)
            segments = path.split('/')
            cwd = result
            for segment in segments[:-1]:
                try:
                    cwd = cwd[segment]
                except KeyError:
                    raise ValueError('Missing parent dir for path %r' % path)
            if kind_data[0] == 'dir':
                cwd[segments[-1]] = {}
            else:
                cwd[segments[-1]] = kind_data
        return result


class DiskUpdater(object):
    """Create a journal based on local disk and a tree representation.

    You can get a tree representation by using a Combiner to combine several
    journals (including a full snapshot, or starting from empty).

    :ivar tree: The tree to compare with.
    :ivar transport: The transport to read disk data from.
    :ivar last_timestamp: The timestamp of the most recent journal: all files
        modified more than 3 seconds before this timestamp are assumed to be
        unchanged.
    :ivar ui: A ui object to send output to.
    :ivar journal: The journal being built up.
    :ivar name: The name of the mirror set the journal will be updating. Used
        to include the mirror definition.
    :ivar include_re: The compiled re that, when it matches, indicates a path
        should be included.
    :ivar exclude_re: The compield re that, when it matches, indicates a path
        should only be included if it also matches the include_re. Note that
        only the exact path is considered: if you have an exclude rule '^foo'
        and an include rule '^foo/bar', once the directory 'foo' is excluded,
        'foo/bar' will not be examined and thus wont end up included. To deal
        with cases like that, either use a negative lookahead instead - exclude
        '^foo/(?!bar(?$|/)', or exclude paths starting with foo, and include
        both foo and bar explicitly: exclude '^foo(?:$|/)' and include '^foo$',
        '^foo/bar(?$|/)'.
    """

    def __init__(self, tree, transport, name, last_timestamp, ui,
        excludes=(), includes=()):
        """Create a DiskUpdater.

        :param tree: The tree to compare with.
        :param transport: The transport to read disk data from.
        :param name: The mirror set name, used to include its config in the
            mirror definition.
        :param last_timestamp: The timestamp of the most recent journal: all
            files modified more than 3 seconds before this timestamp are
            assumed to be unchanged. 3 seconds is chosen because it is larger
            than the 2 second fuzz needed to deal with FAT file systems.
        :param ui: A ui object to send output to.
        :param excludes: An optional list of uncompiled regexes to include in
            the exclude_re.
        :param includes: An optional list of uncompiled regexes to include in
            the include_re.
        """
        self.tree = tree
        self.transport = transport
        self.name = name
        self.last_timestamp = last_timestamp
        self.ui = ui
        self.journal = Journal()
        includes = [r'(?:^|/)\.lmirror/sets(?:$|/%s(?:$|/))' % name
            ] + list(includes)
        self.include_re = re.compile(self._make_re_str(includes))
        excludes = [r'(?:^|/)\.lmirror/'] + list(excludes)
        self.exclude_re = re.compile(self._make_re_str(excludes))

    def _make_re_str(self, re_strs):
        re_strs = ['(?:%s)' % re_str for re_str in re_strs]
        return '|'.join(re_strs)

    def finished(self):
        """Return the journal obtained by scanning the disk."""
        pending = ['']
        while pending:
            dirname = pending.pop(-1)
            names = self.transport.list_dir(dirname)
            # NB: quadratic in lookup here due to presence in inner loop:
            # consider tuning.
            segments = dirname.split('/')
            cwd = self.tree
            for segment in segments:
                if not segment:
                    continue
                try:
                    cwd = cwd[segment]
                except KeyError:
                    # totally new directory - added to journal by the directory
                    # above.
                    cwd = {}
            tree_names = set(cwd)
            names = set(names)
            for name in tree_names - names:
                # deletes
                path = dirname and ('%s/%s' % (dirname, name)) or name
                old_kind_details = cwd[name]
                if type(old_kind_details) is dict:
                    self._gather_deleted_dir(path, cwd[name])
                    old_kind_details = ('dir',)
                self.journal.add(path, 'del',
                    old_kind_details)
            new_names = names - tree_names
            for name in names:
                path = dirname and ('%s/%s' % (dirname, name)) or name
                if self._skip_path(path):
                    continue
                statinfo = self.transport.stat(path)
                # Is it old enough to not check
                mtime = getattr(statinfo, 'st_mtime', 0)
                if self.last_timestamp - mtime > 3 and name not in new_names:
                    continue
                kind = osutils.file_kind_from_stat_mode(statinfo.st_mode)
                if kind == 'file':
                    f = self.transport.get(path)
                    try:
                        disk_size, disk_sha1 = osutils.size_sha_file(f)
                    finally:
                        f.close()
                    new_kind_details = (kind, disk_sha1, disk_size)
                elif kind == 'symlink':
                    new_kind_details = (kind, os.readlink(self.transport.local_abspath(path)))
                elif kind == 'directory':
                    new_kind_details = ('dir',)
                    pending.append(path)
                else:
                    raise ValueError('unknown kind %r for %r' % (kind, path))
                if name in new_names:
                    self.journal.add(path, 'new', new_kind_details)
                else:
                    old_kind_details = cwd[name]
                    if type(old_kind_details) is dict:
                        old_kind_details = ('dir',)
                    if old_kind_details != new_kind_details:
                        self.journal.add(path, 'replace', (old_kind_details,
                            new_kind_details))
        for path, (action, details) in self.journal.paths.iteritems():
            self.ui.output_log(4, __name__, 'Journalling action %s for %r' % (
                action, path))
        return self.journal

    def _gather_deleted_dir(self, path, dirdict):
        # List what the tree thought it had as deletes.
        pending = [(path, dirdict)]
        while pending:
            dirname, cwd = pending.pop(-1)
            for name, old_kind_details in cwd:
                path = dirname and ('%s/%s' % (dirname, name)) or name
                if type(old_kind_details) is dict:
                    pending.append((path, old_kind_details))
                    old_kind_details = ('dir',)
                self.journal.add(path, 'del', old_kind_details)

    def _skip_path(self, path):
        """Should path be skipped?"""
        if (path.endswith('.lmirror/metadata') or
            path.endswith('.lmirrortemp')):
            # metadata is transmitted by the act of fetching the
            # journal.
            return True
        if self.exclude_re.search(path) and not self.include_re.search(path):
            return True
        return False


class Journal(object):
    """A journal of changes to a file system.
    
    :ivar paths: The paths that the journal alters. A dict from path to 
        action, kind_data.
    """

    def __init__(self):
        """Create a Journal."""
        self.paths = {}

    def add(self, relpath, action, kind_data):
        """Add a path to the journal.
        
        :param relpath: The path to journal.
        :param action: One of new, del, replace.
        :param kind_data: The data for the thing being added/deleted/replaced.
            In the special case of replacement this should be a two-tuple of
            the old data and the new data.
        """
        if relpath in self.paths:
            raise ValueError('path %r is already in use.' % relpath)
        if action == 'replace':
            if len(kind_data) != 2 or type(kind_data[0]) is not tuple:
                raise ValueError(
                    'looks like only one kind_data in replace action: %r' %
                    (kind_data,))
        self.paths[relpath] = (action, kind_data)

    def as_bytes(self):
        """Return a byte representation of this journal.

        The representation can be parsed by l_mirror.journals.parse. The
        structure is a header ('l-mimrror-journal-1\n') followed by '\\0'
        delimited fields. These follow the sequence PATH, ACTION, KIND_DATA and
        mirror the parameters to ``add``.

        :return: A bytesequence.
        """
        order = sorted(self.paths.items())
        output = []
        for path, (action, kind_data) in order:
            output.append(path)
            output.append(action)
            if action == 'replace':
                output.extend(kind_data[0])
                if type(output[-1]) is int:
                    output[-1] = str(output[-1])
                output.extend(kind_data[1])
            else:
                output.extend(kind_data)
            if type(output[-1]) is int:
                output[-1] = str(output[-1])
        return 'l-mirror-journal-1\n' + '\0'.join(output)


def parse(a_bytestring):
    """Parse a_bytestring into a journal.
    
    :return: A Journal.
    """
    header = 'l-mirror-journal-1\n'
    if not a_bytestring.startswith(header):
        raise ValueError('Not a journal: missing header %r in %r' % (
            header, a_bytestring))
    content = a_bytestring[len(header):]
    tokens = content.split('\x00')
    result = Journal()
    pos = 0
    if tokens[-1] == '':
        del tokens[-1]
    def parse_kind_data(pos):
        kind = tokens[pos]
        pos += 1
        if kind == 'file':
            return (kind, tokens[pos], int(tokens[pos+1])), pos + 2
        elif kind == 'dir':
            return (kind,), pos
        elif kind == 'symlink':
            return (kind, tokens[pos]), pos + 1
        else:
            raise ValueError('unknown kind %r at token %d.' % (kind, pos))
    while pos < len(tokens):
        path = tokens[pos]
        pos += 1
        action = tokens[pos]
        pos += 1
        if action in ('new', 'del'):
            kind_data, pos = parse_kind_data(pos)
        elif action == 'replace':
            kind_data1, pos = parse_kind_data(pos)
            kind_data2, pos = parse_kind_data(pos)
            kind_data = kind_data1, kind_data2
        result.add(path, action, kind_data)
    return result


class TransportReplay(object):
    """Replay a journal reading content from a transport.

    The replay() method is the main interface.
    
    :ivar sourcedir: The transport to read from.
    :ivar contentdir: The transport to apply changes to.
    :ivar journal: The journal to apply.
    :ivar ui: A UI for reporting with.
    """

    def __init__(self, journal, sourcedir, contentdir, ui):
        """Create a TransportReplay for journal from sourcedir to contentdir.

        :param journal: The journal to replay.
        :param sourcedir: The transport to read from.
        :param contentdir: The transport to apply changes to.
        :param ui: The ui to use for reporting.
        """
        self.journal = journal
        self.sourcedir = sourcedir
        self.contentdir = contentdir
        self.ui = ui

    def replay(self):
        """Replay the journal."""
        adds = []
        deletes = []
        replaces = []
        for path, (action, content) in self.journal.paths.iteritems():
            if action == 'new':
                adds.append((path, content))
            elif action == 'del':
                deletes.append((path, content))
            elif action == 'replace':
                replaces.append((path, content[0], content[1]))
            else:
                raise ValueError('unknown action %r for %r' % (action, path))
        # Ordering /can/ be more complex than just adds/replace/deletes:
        # might have an add blocked on a replace making a dir above it. Likewise
        # A delete might have to happen before a replace when a dir becomes a 
        # file. When we do smarter things, we'll have to just warn that we may
        # not honour general goals/policy if the user has given us such a
        # transform.
        # For now, simplest thing possible - want to get the concept performance
        # evaluated.
        adds.sort()
        for path, content in adds:
            self.put_with_check(path, content)()
        replaces.sort(reverse=True)
        to_rename = []
        try:
            for path, _, new_content in replaces:
                # TODO: (again, to do with replacing files with dirs:)
                #       do not delay creating dirs needed for files below them.
                to_rename.append(self.put_with_check(path, new_content))
            for path, old_content, new_content in replaces:
                # TODO: we may want to warn or perhaps have a strict mode here.
                # e.g. handle already deleted things. This should become clear
                # when recovery mode is done.
                self.contentdir.delete(path)
        finally:
            for doit in to_rename:
                doit()
        # Children go first :)
        deletes.sort(reverse=True)
        for path,content in deletes:
            self.ui.output_log(4, __name__, 'Deleting %s %r' % (content[0], path))
            try:
                if content[0] != 'dir':
                    self.contentdir.delete(path)
                else:
                    self.contentdir.rmdir(path)
            except errors.NoSuchFile:
                # Already gone, ignore it.
                pass

    def ensure_dir(self, path):
        """Ensure that path is a dir.

        If the path exists and is not a dir, an error is raised.
        """
        try:
            self.contentdir.mkdir(path)
        except errors.FileExists:
            st = self.contentdir.stat(path)
            if osutils.file_kind_from_stat_mode(st.st_mode) != 'directory':
                raise ValueError('unexpected non-directory at %r' % path)

    def check_file(self, path, content):
        """Check if there is a file at path with content.

        :raises: ValueError if there a non-file at path.
        :return: True if there is a file present with the right content.
        """
        try:
            st = self.contentdir.stat(path)
            if osutils.file_kind_from_stat_mode(st.st_mode) != 'file':
                raise ValueError('unexpected non-file at %r' % path)
            f = self.contentdir.get(path)
            try:
                size, sha1 = osutils.size_sha_file(f)
            finally:
                f.close()
            return sha1 == content[1] and size == content[2]
        except errors.NoSuchFile:
            return False

    def ensure_file(self, tempname, path, content):
        """Ensure that there is a file with content content at path.

        :param tempname: The name of a temporary file with the needed content.
        """
        if self.check_file(path, content):
            # Note that this implies we copied a file we didn't - during
            # a complete resync - sure, but still not optimal bw use.
            self.contentdir.delete(tempname)
        self.contentdir.rename(tempname, path)

    def ensure_link(self, realpath, target):
        """Ensure that realpath is a link to target.
        
        An error is raised if something is in the way.
        """
        try:
            os.symlink(content[1], realpath)
        except OSerror, e:
            if e.errno == errno.EEXIST:
                st = os.lstat(realpath)
                if osutils.file_kind_from_stat_mode(st.st_mode) != 'symlink':
                    raise ValueError('unexpected non-symlink at %r' % realpath)
                os.unlink(realpath)
                os.symlink(content[1], realpath)
            else:
                raise

    def put_with_check(self, path, content):
        """Put a_file at path checking that as received it matches content.

        :param path: A relpath.
        :param content: A content description of a file.
        :return: A callable that will execute the rename-into-place - all the
            IO has been done before returning.
        """
        tempname = '%s.lmirrortemp' % path
        self.ui.output_log(4, __name__, 'Writing %s %r' % (content[0], path))
        if content[0] == 'dir':
            return lambda: self.ensure_dir(path)
        elif content[0] == 'symlink':
            realpath = self.sourcedir.local_abspath(path)
            return lambda: self.ensure_link(realpath, content[1])
        elif content[0] != 'file':
            raise ValueError('unknown kind %r for %r' % (content[0], path))
        # don't download content we don't need
        try:
            if self.check_file(path, content):
                return lambda:None
        except ValueError:
            pass
        a_file = self.sourcedir.get(path)
        source = _ShaFile(a_file)
        try:
            # FIXME: mode should be supplied from above, or use 0600 and chmod
            # later.
            stream = self.contentdir.open_write_stream(tempname, 0644)
            try:
                size = osutils.pumpfile(source, stream)
            finally:
                stream.close()
            # TODO: here is where we should check for a mirror-is-updating
            # case.
            if size != content[2] or source.sha1.hexdigest() != content[1]:
                self.contentdir.delete(tempname)
                raise ValueError(
                    'read incorrect content for %r, got sha %r wanted %r' % (
                    path, source.sha1.hexdigest(), content[1]))
        finally:
            a_file.close()
        return lambda: self.ensure_file(tempname, path, content)


class _ShaFile(object):
    """Pretend to be a file, calculating the sha and size.
    
    After reading from this file, access the sha1 and size attributes to
    get the sha and size.

    XXX: I'm sure this is a dup with something bzrlib or somewhere else. Find
    and reuse.

    :ivar sha1: A sha1 object.
    """

    def __init__(self, a_file):
        self.a_file = a_file
        self.sha1 = sha()

    def read(self, amount=None):
        result = self.a_file.read(amount)
        self.sha1.update(result)
        return result
