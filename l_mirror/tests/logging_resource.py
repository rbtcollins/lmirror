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

"""A test resource to provide isolation for the logging module (sigh, globals)."""

__all__ = ['LoggingResourceManager']

import logging

from testresources import TestResourceManager

from l_mirror.tests.monkeypatch import monkeypatch


class OldState:

    def __init__(self, restore_functions):
        self.restore_functions = restore_functions

    def tearDown(self):
        for fn in self.restore_functions:
            fn()


class LoggingResourceManager(TestResourceManager):
    """A resource for testing logging module using code.

    This resource resets the global logging state around a test.
    """

    def __getattribute__(self, attr):
        if attr == '_dirty':
            return True
        return object.__getattribute__(self, attr)

    def make(self, dep_resources):
        new_root = logging.RootLogger(logging.WARNING)
        new_manager = logging.Manager(new_root)
        new_manager.emittedNoHandlerWarning = 1
        return OldState([monkeypatch('logging.root', new_root),
            monkeypatch('logging.Logger.root', new_root),
            monkeypatch('logging.Logger.manager', new_manager)])

    def isDirty(self):
        return True

    def clean(self, resource):
        resource.tearDown()
