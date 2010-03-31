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

"""Helper to make bzrlib memory transport's stat return st_mtime's of 0."""

__all__ = ['install']

from bzrlib.transport.memory import MemoryTransport

import monkeypatch


def install():
    """Install the patch."""
    return monkeypatch.monkeypatch(
        'bzrlib.transport.memory.MemoryTransport.stat', add_mtime)

real_stat = MemoryTransport.stat
def add_mtime(self, relpath):
    result = real_stat(self, relpath)
    result.st_mtime = 0
    return result
