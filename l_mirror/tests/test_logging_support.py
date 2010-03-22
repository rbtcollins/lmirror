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

"""Tests for logging support code."""

from StringIO import StringIO
import logging
import os.path
import time

from l_mirror import logging_support
from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.logging_resource import LoggingResourceManager
from l_mirror.tests.stubpackage import TempDirResource


class TestLoggingSetup(ResourcedTestCase):

    resources = [('logging', LoggingResourceManager())]

    def test_configure_logging_sets_converter(self):
        out = StringIO()
        c_log, f_log, formatter = logging_support.configure_logging(out)
        self.assertEqual(c_log, logging.root.handlers[0])
        self.assertEqual(f_log, logging.root.handlers[1])
        self.assertEqual(None, c_log.formatter)
        self.assertEqual(formatter, f_log.formatter)
        self.assertEqual(time.gmtime, formatter.converter)
        self.assertEqual("%Y-%m-%d %H:%M:%SZ", formatter.datefmt)
        self.assertEqual(logging.StreamHandler, c_log.__class__)
        self.assertEqual(out, c_log.stream)
        self.assertEqual(logging.FileHandler, f_log.__class__)
        self.assertEqual(os.path.expanduser("~/.cache/lmirror/log"), f_log.baseFilename)

    def test_can_supply_filename_None(self):
        out = StringIO()
        c_log, f_log, formatter = logging_support.configure_logging(out, None)
        self.assertEqual(None, f_log)
