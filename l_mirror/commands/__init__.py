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

"""'Commands' for lmirror.

The code in this module contains the Command base class, which provides stock
UI agnostic support for commands - top level actions that users take.

Actual commands can be found in l_mirror.commands.$commandname.

For example, l_mirror.commands.init is the init command name, and 
l_mirror.command.foo_bar would be the foo-bar command (if one
existed). The Command discovery logic looks for a class in the module with
the same name - e.g. l_mirro.commands.init.init would be the class.
That class must obey the l_mirror.commands.Command protocol, but does
not need to be a subclass.

Plugins and extensions wanting to add commands should install them into
l_mirror.commands (perhaps by extending the l_mirror.commands
__path__ to include a directory containing their commands - no __init__ is
needed in that directory.)
"""

__all__ = ['iter_commands', 'Command']

import os
import sys


def _find_command(cmd_name):
    cmd_name = cmd_name.replace('-', '_')
    classname = "%s" % cmd_name
    modname = "l_mirror.commands.%s" % cmd_name
    try:
        _temp = __import__(modname, globals(), locals(), [classname])
    except ImportError, e:
        raise KeyError("Could not import command module %s: %s" % (
            modname, e))
    result = getattr(_temp, classname, None)
    if result is None:
        raise KeyError(
            "Malformed command module - no command class %s found in module %s."
            % (classname, modname))
    if getattr(result, 'name', None) is None:
        # Store the name for the common case of name == lookup path.
        result.name = classname
    return result


def iter_commands():
    """Iterate over all the command classes."""
    paths = __path__
    names = set()
    for path in paths:
        # For now, only support regular installs. TODO: support zip, eggs.
        for filename in os.listdir(path):
            base = os.path.basename(filename)
            if base.startswith('.'):
                continue
            name = base.split('.', 1)[0]
            names.add(name)
    names.discard('__init__')
    names = sorted(names)
    for name in names:
        yield _find_command(name)


class Command(object):
    """A command that can be run.

    Commands contain non-UI non-domain specific behaviour - they are the
    glue between the UI and the object model.

    Commands are parameterised with:
    :ivar ui: a UI object which is responsible for brokering the command
        arguments, input and output. There is no default ui, it must be
        passed to the constructor.
    
    Commands declare that they accept/need/emit:
    :ivar args: A list of l_mirror.arguments.AbstractArgument instances.
        AbstractArgument arguments are validated when set_command is called on
        the UI layer.
    :ivar input_streams: A list of stream specifications. Mandatory streams
        are specified by a simple name. Optional streams are specified by
        a simple name with a ? ending the name. Optional multiple streams are
        specified by a simple name with a * ending the name, and mandatory
        multiple streams by ending the name with +. Multiple streams are used
        when a command can process more than one stream.
    :ivar options: A list of optparse.Option options to accept. These are
        merged with global options by the UI layer when set_command is called.
    """

    # class defaults to no streams.
    input_streams = []
    # class defaults to no arguments.
    args = []
    # class defaults to no options.
    options = []

    def __init__(self, ui):
        """Create a Command object with ui ui."""
        self.ui = ui
        self._init()

    def execute(self):
        """Execute a command.

        This interrogates the UI to ensure that arguments and options are
        supplied, performs any validation for the same that the command needs
        and finally calls run() to perform the command. Most commands should
        not need to override this method, and any user wanting to run a 
        command should call this method.

        This is a synchronous method, and basically just a helper. GUI's or
        asynchronous programs can choose to not call it and instead should call
        lower level API's.
        """
        if not self.ui.set_command(self):
            return 1
        try:
            result = self.run()
        except Exception:
            error_tuple = sys.exc_info()
            self.ui.output_error(error_tuple)
            return 3
        if not result:
            return 0
        return result

    @classmethod
    def get_summary(klass):
        docs = klass.__doc__.split('\n')
        return docs[0]

    def _init(self):
        """Per command init call, called into by Command.__init__."""

    def run(self):
        """The core logic for this command to be implemented by subclasses."""
        raise NotImplementedError(self.run)
