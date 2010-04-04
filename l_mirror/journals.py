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


class PathContent(object):
    """Content about a path.

    This is an abstract type with enough data to verify whether a given path
    has been updated correctly or not.

    :ivar kind: The kind of the path.
    """

    def __hash__(self):
        return hash(tuple(self.as_tokens()))

    def __eq__(self, other):
        return type(other) == type(self) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other

    def as_tokens(self):
        """Return a list of the tokens that would parse into this PathContent.
        
        :return: A list of tokens.
        """
        raise NotImplementedError(self.as_tokens)

    def __repr__(self):
        return "PathContent: '%s'" % (self.as_tokens(),)


class FileContent(PathContent):
    """Content for files.
    
    :ivar sha1: The sha1 of the filec ontent.
    :ivar length: The length of the file.
    :ivar mtime: The mtime of the file. None if it is not known.
    """

    def __init__(self, sha1, length, mtime):
        self.kind = 'file'
        self.sha1 = sha1
        self.length = length
        self.mtime = mtime

    def as_tokens(self):
        if self.mtime is None:
            mtime = "None"
        else:
            mtime = "%0.6f" % self.mtime
        return [self.kind, self.sha1, str(self.length), mtime]


class SymlinkContent(PathContent):
    """Content for symlinks."""

    def __init__(self, target):
        self.kind = 'symlink'
        self.target = target

    def as_tokens(self):
        return [self.kind, self.target]


class DirContent(PathContent):
    """Content for directories."""

    def __init__(self):
        self.kind = 'dir'

    def as_tokens(self):
        return [self.kind]


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
            if kind_data.kind == 'dir':
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
                    new_kind_details = FileContent(disk_sha1, disk_size, statinfo.st_mtime)
                elif kind == 'symlink':
                    new_kind_details = SymlinkContent(os.readlink(self.transport.local_abspath(path)))
                elif kind == 'directory':
                    new_kind_details = DirContent()
                    pending.append(path)
                else:
                    raise ValueError('unknown kind %r for %r' % (kind, path))
                if name in new_names:
                    self.journal.add(path, 'new', new_kind_details)
                else:
                    old_kind_details = cwd[name]
                    if type(old_kind_details) is dict:
                        old_kind_details = DirContent()
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
            if len(kind_data) != 2 or not isinstance(kind_data[0], PathContent):
                raise ValueError(
                    'looks like only one kind_data in replace action: %r' %
                    (kind_data,))
        self.paths[relpath] = (action, kind_data)

    def as_bytes(self):
        """Return a byte representation of this journal.

        The representation can be parsed by l_mirror.journals.parse. The
        structure is a header ('l-mimrror-journal-2\n') followed by '\\0'
        delimited tokens. These follow the sequence PATH, ACTION, KIND_DATA* and
        mirror the parameters to ``add``.

        :return: A bytesequence.
        """
        order = sorted(self.paths.items())
        output = []
        for path, (action, kind_data) in order:
            output.append(path)
            output.append(action)
            if action == 'replace':
                output.extend(kind_data[0].as_tokens())
                output.extend(kind_data[1].as_tokens())
            else:
                output.extend(kind_data.as_tokens())
        return 'l-mirror-journal-2\n' + '\0'.join(output)

    def as_groups(self):
        """Create a series of groups that can be acted on to apply the journal.
        
        :Return: An iterator of groups. Each group is a list of (action, path,
            content).
        """
        groups = []
        adds = []
        deletes = []
        replaces = []
        for path, (action, content) in self.paths.iteritems():
            if action == 'new':
                adds.append((action, path, content))
            elif action == 'del':
                deletes.append((action, path, content))
            elif action == 'replace':
                replaces.append((action, path, content))
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
        replaces.sort(reverse=True)
        # Children go first when deleting a tree
        deletes.sort(reverse=True)
        return  [adds, replaces, deletes]


def parse(a_bytestring):
    """Parse a_bytestring into a journal.
    
    :return: A Journal.
    """
    header1 = 'l-mirror-journal-1\n'
    header2 = 'l-mirror-journal-2\n'
    if not a_bytestring.startswith(header1):
        if not a_bytestring.startswith(header2):
            raise ValueError('Not a journal: missing header %r' % (
                a_bytestring,))
        else:
            def parse_kind_data(tokens, pos):
                kind = tokens[pos]
                pos += 1
                if kind == 'file':
                    return FileContent(tokens[pos], int(tokens[pos+1]), float(tokens[pos+2])), pos + 3
                elif kind == 'dir':
                    return DirContent(), pos
                elif kind == 'symlink':
                    return SymlinkContent(tokens[pos]), pos + 1
                else:
                    raise ValueError('unknown kind %r at token %d.' % (kind, pos))
            content = a_bytestring[len(header2):]
    else:
        def parse_kind_data(tokens, pos):
            kind = tokens[pos]
            pos += 1
            if kind == 'file':
                return FileContent(tokens[pos], int(tokens[pos+1]), None), pos + 2
            elif kind == 'dir':
                return DirContent(), pos
            elif kind == 'symlink':
                return SymlinkContent(tokens[pos]), pos + 1
            else:
                raise ValueError('unknown kind %r at token %d.' % (kind, pos))
        content = a_bytestring[len(header1):]
    tokens = content.split('\x00')
    result = Journal()
    pos = 0
    if tokens[-1] == '':
        del tokens[-1]
    while pos < len(tokens):
        path = tokens[pos]
        pos += 1
        action = tokens[pos]
        pos += 1
        if action in ('new', 'del'):
            kind_data, pos = parse_kind_data(tokens, pos)
        elif action == 'replace':
            kind_data1, pos = parse_kind_data(tokens, pos)
            kind_data2, pos = parse_kind_data(tokens, pos)
            kind_data = kind_data1, kind_data2
        result.add(path, action, kind_data)
    return result


class Action(object):
    """An action that can be taken.
    
    :ivar type: new/replace/del - the action type.
    :ivar path: The path being acted on.
    :ivar content: The content being acted on. For deletes the old content, for
        new the content, and for replaces the old, new content.
    """
    
    def __init__(self, action_type, path, content):
        """Create an Action."""
        self.type = action_type
        self.path = path
        self.content = content

    def as_bytes(self):
        """Return a generator of bytes for this action.

        This contains the type
        
        :param sourcedir: A Transport to read new file content from.
        """
        if self.type == 'replace':
            content_list = []
            content_list.extend(self.content[0].as_tokens())
            content_list.extend(self.content[1].as_tokens())
            content_bytes = "\x00".join(content_list)
            content = self.content[1]
        else:
            content_bytes = '\x00'.join(self.content.as_tokens())
            if self.type == 'new':
                content = self.content
            else:
                content = None
        yield "%s\x00%s\x00%s\x00" % (self.path, self.type, content_bytes)
        if content and content.kind == 'file':
            source = self.get_file()
            remaining = content.length
            while remaining:
                read_size = min(remaining, 65536)
                read_content = source.read(read_size)
                remaining -= len(read_content)
                if not read_content:
                    raise ValueError('0 byte read, expected %d' % read_size)
                yield read_content

    def get_file(self):
        """Get a file like object for file content for this action."""
        raise NotImplementedError(self)

    def ignore_file(self):
        """Tell the action that its file content is being skipped."""


class TransportAction(Action):
    """An Action which gets file content from a transport.
    
    :ivar sourcedir: Transport to read file content from.
    """

    def __init__(self, action_type, path, content, sourcedir):
        Action.__init__(self, action_type, path, content)
        self.sourcedir = sourcedir

    def get_file(self):
        """Get the content for a new file as a file-like object."""
        return self.sourcedir.get(self.path)


class StreamedAction(Action):
    """An Action which gets file content from a FromFileGenerator."""

    def __init__(self, action_type, path, content, generator):
        Action.__init__(self, action_type, path, content)
        self.generator = generator

    def get_file(self):
        if self.type == 'replace':
            content = self.content[1]
        else:
            content = self.content
        if content.kind != 'file':
            raise ValueError('invalid call to get_file: kind is %r' %
                content.kind)
        return BufferedFile(self.generator, content.length)

    def ignore_file(self):
        self.get_file().close()


class BufferedFile(object):
    """A file-like object which reads from a FromFileGenerator's stream."""

    def __init__(self, generator, remaining):
        self.generator = generator
        self.remaining = remaining

    def read(self, count=None):
        if count is None:
            count = self.remaining
        read_size = min(self.remaining, count)
        if not read_size:
            return ''
        read_content = self.generator._next_bytes(read_size)
        self.remaining -= len(read_content)
        return read_content

    def close(self):
        while self.remaining:
            self.read()


class ReplayGenerator(object):
    """Generate the data needed to perform a replay of a journal.

    The stream method returns a generator of objects which can be either
    converted to an action, or to bytes.

    :ivar journal: The journal being generated from.
    :ivar sourcedir: The transport content is read from.
    :ivar ui: A UI for reporting with.
    """

    def __init__(self, journal, sourcedir, ui):
        """Create a ReplayGenerator.

        :param journal: The journal to replay.
        :param sourcedir: The transport to read from.
        :param ui: The ui to use for reporting.
        """
        self.journal = journal
        self.sourcedir = sourcedir
        self.ui = ui

    def stream(self):
        """Generate the stream."""
        groups = self.journal.as_groups()
        for group in groups:
            for action, path, content in group:
                yield TransportAction(action, path, content, self.sourcedir)

    def as_bytes(self):
        """Return a generator of bytestrings for this generator's content."""
        for item in self.stream():
            for segment in item.as_bytes():
                yield segment


class FromFileGenerator(object):
    """A ReplayGenerator that pulls from a file in read-once, no-seeking mode.

    This is used for streaming from HTTP servers.
    """

    def __init__(self, stream):
        self._stream = stream
        self.buffered_bytes = []

    def parse_kind_data(self, tokens):
        pos = 2
        kind = tokens[pos]
        pos += 1
        if kind == 'file':
            return FileContent(tokens[pos], int(tokens[pos+1]), float(tokens[pos+2])), pos + 3
        elif kind == 'dir':
            return DirContent(), pos
        elif kind == 'symlink':
            return SymlinkContent(tokens[pos]), pos + 1
        else:
            raise ValueError('unknown kind %r at token %d.' % (kind, pos))

    def stream(self):
        """Generate an object-level stream."""
        while True:
            # TODO: make this more efficient: but wait till its shown to be a
            # key issue to address.
            some_bytes = self._next_bytes(4096)
            tokens = some_bytes.split('\x00')
            path = tokens[0]
            action = tokens[1]
            kind = tokens[2]
            if action in ('new', 'del'):
                kind_data, pos = self.parse_kind_data(tokens)
            elif action == 'replace':
                kind_data1, pos = self.parse_kind_data(tokens)
                kind_data2, pos = self.parse_kind_data(tokens)
                kind_data = kind_data1, kind_data2
            else:
                raise ValueError('unknown action %r' % action)
            self._push('\x00'.join(tokens[pos:]))
            yield StreamedAction(action, path, kind_data, self)

    def _next_bytes(self, count):
        """Return up to count bytes.

        :return some bytes: An empty string indicates end of file.
        """
        if count <= 0:
            raise ValueError('attempt to read 0 bytes!')
        if not self.buffered_bytes:
            return self._stream.read(count)
        if count >= len(self.buffered_bytes[0]):
            partial = self.buffered_bytes.pop(0)
            return partial + self._next_bytes(count - len(partial))
        result = self.buffered_bytes[0][:count]
        self.buffered_bytes[0] = self.buffered_bytes[0][count:]
        return result

    def _push(self, unused_bytes):
        self.buffered_bytes.insert(0, unused_bytes)

    def as_bytes(self):
        content = self._stream.read(65536)
        while content:
            yield content
            content = self._stream.read(65536)


class TransportReplay(object):
    """Replay a journal reading content from a transport.

    The replay() method is the main interface.
    
    :ivar generator: A ReplayGenerator to read the actions and content from.
        The generator is not trusted - its actions are cross checked against
        journal.
    :ivar contentdir: The transport to apply changes to.
    :ivar journal: The journal to apply.
    :ivar ui: A UI for reporting with.
    """

    def __init__(self, journal, generator, contentdir, ui):
        """Create a TransportReplay for journal from generator to contentdir.

        :param journal: The journal to replay.
        :param generator: The ReplayGenerator to get new content from. All the
            actions it supplies are cross checked against journal.
        :param contentdir: The transport to apply changes to.
        :param ui: The ui to use for reporting.
        """
        self.journal = journal
        self.generator = generator.stream()
        self.contentdir = contentdir
        self.ui = ui

    def replay(self):
        """Replay the journal."""
        groups = self.journal.as_groups()
        for group in groups:
            elements = set(group)
            to_rename = []
            to_delete = []
            try:
                while elements:
                    action_obj = self.generator.next()
                    # If this fails, generator has sent us some garbage.
                    elements.remove((action_obj.type, action_obj.path,
                        action_obj.content))
                    action = action_obj.type
                    path = action_obj.path
                    content = action_obj.content
                    if action == 'new':
                        self.put_with_check(path, content, action_obj)()
                    if action == 'replace':
                        # TODO: (again, to do with replacing files with dirs:)
                        #       do not delay creating dirs needed for files
                        #       below them.
                        to_rename.append(self.put_with_check(path, content[1],
                            action_obj))
                        to_delete.append((path, content[0]))
                    if action == 'del':
                        to_delete.append((path, content))
                for path, content in to_delete:
                    # Second pass on the group to handle deletes as late as possible
                    # TODO: we may want to warn or perhaps have a strict mode here.
                    # e.g. handle already deleted things. This should become clear
                    # when recovery mode is done.
                    self.ui.output_log(4, __name__, 'Deleting %s %r' %
                        (content.kind, path))
                    try:
                        if content.kind != 'dir':
                            self.contentdir.delete(path)
                        else:
                            self.contentdir.rmdir(path)
                    except errors.NoSuchFile:
                        # Already gone, ignore it.
                        pass
            finally:
                for doit in to_rename:
                    doit()

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
            return sha1 == content.sha1 and size == content.length
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

    def put_with_check(self, path, content, action):
        """Put a_file at path checking that as received it matches content.

        :param path: A relpath.
        :param content: A content description of a file.
        :param action: An action object which can supply file content.
        :return: A callable that will execute the rename-into-place - all the
            IO has been done before returning.
        """
        tempname = '%s.lmirrortemp' % path
        self.ui.output_log(4, __name__, 'Writing %s %r' % (content.kind, path))
        if content.kind == 'dir':
            return lambda: self.ensure_dir(path)
        elif content.kind == 'symlink':
            realpath = self.contentdir.local_abspath(path)
            return lambda: self.ensure_link(realpath, content.target)
        elif content.kind != 'file':
            raise ValueError('unknown kind %r for %r' % (content.kind, path))
        # don't download content we don't need
        try:
            if self.check_file(path, content):
                action.ignore_file()
                return lambda:None
        except ValueError:
            pass
        a_file = action.get_file()
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
            if size != content.length or source.sha1.hexdigest() != content.sha1:
                self.contentdir.delete(tempname)
                raise ValueError(
                    'read incorrect content for %r, got sha %r wanted %r' % (
                    path, source.sha1.hexdigest(), content.sha1))
            if content.mtime is not None:
                try:
                    temppath = self.contentdir.local_abspath(tempname)
                except errors.NotLocalUrl, e:
                    # swallow NotLocalUrl errors: they primarily indicate that
                    # the test suite is running against memory, with files that
                    # don't exist.
                    self.ui.output_log(4, __name__,
                        'Failed to set mtime for %r - nonlocal url %r.' % (
                        tempname, self.contentdir))
                else:
                    # Perhaps the first param - atime - should be 'now'.
                    os.utime(temppath, (content.mtime, content.mtime))
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
