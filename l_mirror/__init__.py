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

"""The l_mirror library.

This library is divided into some broad areas.

The arguments package contains command argument parsing facilities.
The commands package contains the main user entry points into the application.
The ui package contains various user interfaces.
The journals module contains logic for working with individual journals.
The mirrorset module contains logic for working with a mirrorset - a thing to
    be mirrored around.
The tests package contains tests and test specific support code.
"""

__all__ = ['version', '__version__']

import pbr.version

# same format as sys.version_info: "A tuple containing the five components of
# the version number: major, minor, micro, releaselevel, and serial. All
# values except releaselevel are integers; the release level is 'alpha',
# 'beta', 'candidate', or 'final'. The version_info value corresponding to the
# Python version 2.0 is (2, 0, 0, 'final', 0)."  Additionally we use a
# releaselevel of 'dev' for unreleased under-development code.
#
# If the releaselevel is 'alpha' then the major/minor/micro components are not
# established at this point, and setup.py will use a version of next-$(revno).
# If the releaselevel is 'final', then the tarball will be major.minor.micro.
# Otherwise it is major.minor.micro~$(revno).

# Uncomment when pbr 0.11 is released.
#_version = pbr.version.VersionInfo('lmirror').semantic_version()
#__version__ = _version.version_tuple()
#version = _version.release_string()
__version__ = (0, 0, 4, 'alpha', 0)
