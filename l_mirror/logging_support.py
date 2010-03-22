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

"""Useful generic logging config stuff, mainly used by l_mirror.ui.cl."""

__all__ = ['configure_logging']

import logging
import os.path
import time

from bzrlib import transport

def configure_logging(console_stream, f_path="~/.cache/lmirror/log"):
    """Configure a formatter and create a console and file handlers.

    The formatter is setup for ISO8601 UTC logging.

    :param console_stream: A stream to log to for console events.
    :param f_path: Optional path to configure for the file logging (used in
        testing). Use None to disable file logging.
    :return (console_log_handler, file_log_handler, formatter).
    """
    f_formatter = logging.Formatter("%(asctime)s: %(message)s", "%Y-%m-%d %H:%M:%SZ")
    f_formatter.converter = time.gmtime
    console_handler = logging.StreamHandler(console_stream)
    # console_handler.setFormatter(formatter)
    # Capture root events
    logger = logging.getLogger()
    logger.addHandler(console_handler)
    logger.setLevel(0)
    if f_path is None:
        file_handler = None
    else:
        f_path = os.path.expanduser(f_path)
        if not os.path.exists(f_path):
            t = transport.get_transport(f_path).clone('..')
            t.create_prefix()
        file_handler = logging.FileHandler(f_path)
        file_handler.setFormatter(f_formatter)
        logger.addHandler(file_handler)
    return console_handler, file_handler, f_formatter

    return None, None, None
