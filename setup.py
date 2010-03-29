#!/usr/bin/env python
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

from distutils.core import setup
import os

import l_mirror

version = '.'.join(str(component) for component in l_mirror.__version__[0:3])
phase = l_mirror.__version__[3]
if phase != 'final':
    import bzrlib.workingtree
    t = bzrlib.workingtree.WorkingTree.open_containing(__file__)[0]
    if phase == 'alpha':
        # No idea what the next version will be
        version = 'next-%s' % t.branch.revno()
    else:
        # Preserve the version number but give it a revno prefix
        version = version + '~%s' % t.branch.revno()

description = file(os.path.join(os.path.dirname(__file__), 'README.txt'), 'rb').read()

setup(name='lmirror',
      author='Robert Collins',
      author_email='robertc@robertcollins.net',
      url='https://launchpad.net/lmirror',
      description='Large scale mirror protocol.',
      long_description=description,
      scripts=['lmirror'],
      version=version,
      packages=[
        'l_mirror',
        'l_mirror.arguments',
        'l_mirror.commands',
        'l_mirror.ui',
        'l_mirror.tests',
        'l_mirror.tests.arguments',
        'l_mirror.tests.commands',
        'l_mirror.tests.ui',
        ])
