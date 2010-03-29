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

"""LMirror local gpg support."""

__all__ = ['SimpleGPGStrategy']

import subprocess
import sys

from bzrlib import gpg

class SimpleGPGStrategy(gpg.GPGStrategy):
    """A simple signing strategy that does not need configuration.

    :seealso bzrlib.gpg.GPGStrategy: The base class in bzrlib that needs
        configuration.

    This also does plain signs, rather than clearsigned signatures.
    """

    def _command_line(self):
        return ['gpg', '--detach-sign']


class GPGVStrategy(object):
    """Class for performing GPGV calls.
    
    :ivar keyringpath: The path to the keyring to validate against.
    :ivar ui: A UI object.
    """

    def __init__(self, keyringpath, ui):
        self.keyringpath = keyringpath
        self.ui = ui

    def verify(self, sigdir, signame, content):
        """Check that content is validly signed.

        :param sigdir: Transport that the signature can be found on.
        :param signame: The name of the signature.
        :param content: The content that should be signed.
        """
        sigpath = sigdir.local_abspath(signame)
        # Using the shell gives us solid sigpipe handling, strange but true.
        encoding = sys.getfilesystemencoding()
        # The string join is so that the shell is given the correct arguments:
        # this appears to be a subprocess bug.
        proc = self.ui.subprocess_Popen(' '.join(['gpgv', '--keyring',
            self.keyringpath.encode(encoding), sigpath.encode(encoding), '-']),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            shell=True
            )
        out, err = proc.communicate(content)
        if proc.returncode != 0:
            self.ui.output_log(9, 'l_mirror.gpg', out)
            raise ValueError("GPG verification failed!")


class TestGPGVStrategy(object):
    """Test class for gpgv invocations.
    
    :ivar expected: The data that should be considered signed in a list, one
        item per call to verify.
    """
    
    def __init__(self, expected):
        self.expected = expected

    def verify(self, sigdir, signame, content):
        expected = self.expected.pop(0)
        if content != expected:
            raise ValueError("different data %r != %r" % (content, expected))
