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

"""Monkeypatch helper function for tests.

This should be moved to testtools or something, its very generic.
"""

def monkeypatch(name, new_value):
    """Replace name with new_value.

    :return: A callable which will restore the original value.
    """
    location, attribute = name.rsplit('.', 1)
    # Import, swallowing all errors as any element of location may be
    # a class or some such thing.
    try:
        __import__(location, {}, {})
    except ImportError:
        pass
    components = location.split('.')
    current = __import__(components[0], {}, {})
    for component in components[1:]:
        current = getattr(current, component)
    old_value = getattr(current, attribute)
    setattr(current, attribute, new_value)
    def restore():
        setattr(current, attribute, old_value)
    return restore
