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

"""An Argument that parses into bzrlib LocalTransport objects."""

__all__ = ['PathArgument']

from bzrlib.transport import get_transport
from bzrlib.errors import NotLocalUrl

from l_mirror.arguments import AbstractArgument


class PathArgument(AbstractArgument):
    """An argument that parses into bzrlib LocalTransport objects."""

    def _parse_one(self, arg):
        result = get_transport(arg)
        # trigger a check that this is local
        try:
            result.local_abspath('.')
        except NotLocalUrl, e:
            if result.base.startswith('memory'):
                # permit fortesting
                pass
            else:
                raise ValueError('Not a local path: %r' % arg)
        return result

