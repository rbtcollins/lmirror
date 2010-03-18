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
"""

__all__ = ['parse', 'Combiner', 'Journal', 'DiskUpdater']

from bzrlib import osutils


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
    """

    def __init__(self, tree, transport, last_timestamp, ui):
        """Create a DiskUpdater.

        :param tree: The tree to compare with.
        :param transport: The transport to read disk data from.
        :param last_timestamp: The timestamp of the most recent journal: all
            files modified more than 3 seconds before this timestamp are
            assumed to be unchanged. 3 seconds is chosen because it is larger
            than the 2 second fuzz needed to deal with FAT file systems.
        :param ui: A ui object to send output to.
        """
        self.tree = tree
        self.transport = transport
        self.last_timestamp = last_timestamp
        self.ui = ui
        self.journal = Journal()

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
                    old_kind_details = ('dir',)
                self.journal.add(path, 'del',
                    old_kind_details)
            new_names = names - tree_names
            for name in names:
                path = dirname and ('%s/%s' % (dirname, name)) or name
                if path.endswith('.lmirror/metadata'):
                    # metadata is transmitted by the act of fetching the
                    # journal.
                    continue
                statinfo = self.transport.stat(path)
                # Is it old enough to not check
                mtime = getattr(statinfo, 'st_mtime', 0)
                if self.last_timestamp - mtime > 3:
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
        return self.journal


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
