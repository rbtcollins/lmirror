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

"""A TestResource that provides a temporary python package."""

import os.path
import shutil
import tempfile

from testresources import TestResource

class TempDirResource(TestResource):
    """A temporary directory resource.  

    This resource is never considered dirty.
    """

    def make(self, dependency_resources):
        return tempfile.mkdtemp()

    def clean(self, resource):
        shutil.rmtree(resource, ignore_errors=True)


class StubPackage(object):
    """A temporary package for tests.
    
    :ivar base: The directory containing the package dir.
    """


class StubPackageResource(TestResource):
    
    def __init__(self, packagename, modulelist, init=True):
        super(StubPackageResource, self).__init__()
        self.packagename = packagename
        self.modulelist = modulelist
        self.init = init
        self.resources = [('base', TempDirResource())]

    def make(self, dependency_resources):
        result = StubPackage()
        base = dependency_resources['base']
        root = os.path.join(base, self.packagename)
        os.mkdir(root)
        init_seen = not self.init
        for modulename, contents in self.modulelist:
            stream = file(os.path.join(root, modulename), 'wb')
            try:
                stream.write(contents)
            finally:
                stream.close()
            if modulename == '__init__.py':
                init_seen = True
        if not init_seen:
            file(os.path.join(root, '__init__.py'), 'wb').close()
        return result
