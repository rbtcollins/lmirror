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

"""A TestResource that provides a temporary homedir package."""

__all__ = ['StubHomeResource']

import os

from testresources import TestResource

from l_mirror.tests.stubpackage import TempDirResource


class StubHome(object):
    """A temporary home dir.
    
    :ivar tempdir: The directory containing the package dir.
    """

    def __init__(self, tempdir):
        self.old_home = os.environ.get('HOME', None)
        os.environ['HOME'] = tempdir

    def tearDown(self):
        if self.old_home is None:
            del os.environ['HOME']
        else:
            os.environ['HOME'] = self.old_home


class StubHomeResource(TestResource):
    
    def __init__(self):
        super(StubHomeResource, self).__init__()
        self.resources = [('tempdir', TempDirResource())]

    def make(self, dependency_resources):
        tempdir = dependency_resources['tempdir']
        result = StubHome(tempdir)
        return result

    def cleanup(self, res):
        res.tearDown()
