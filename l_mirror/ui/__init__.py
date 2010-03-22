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

"""In l_mirror a UI is an interface to a 'user' (which may be a machine).

The l_mirror.ui.cli module contains a command line interface, and the
module l_mirror.ui.model contains a purely object based implementation
which is used for testing l_mirror.

See AbstractUI for details on what UI classes should do and are responsible
for.
"""

class AbstractUI(object):
    """The base class for UI objects, this providers helpers and the interface.

    A UI object is responsible for brokering interactions with a particular
    user environment (e.g. the command line). These interactions can take
    several forms:
     - reading bulk data
     - gathering data
     - emitting progress or activity data - hints as to the programs execution.
     - providing notices about actions taken
     - showing the result of some query (including errors)
    All of these things are done in a structured fashion. See the methods
    iter_streams, query_user, progress, notice and result.

    UI objects are generally expected to be used once, with a fresh one
    created for each command executed.

    :ivar cmd: The command that is running using this UI object.
    :ivar here: The location that command is being run in. This may be a local
        path or a URL. This is only guaranteed to be set after set_command is
        called, as some UI's need to do option processing to determine its
        value.
    :ivar options: The parsed options for this ui, containing both global and
        command specific options.
    :ivar arguments: The parsed arguments for this ui. Set Command.args to
        define the accepted arguments for a command.
    """

    def _check_cmd(self):
        """Check that cmd is valid. This method is meant to be overridden.
        
        :return: True if the cmd is valid - if options and args match up with
            the ones supplied to the UI, and so on.
        """

    def iter_streams(self, stream_type):
        """Iterate over all the streams of type stream_type.

        Implementors of UI should implement _iter_streams which is called after
        argument checking is performed.

        :param stream_type: A simple string such as 'subunit' which matches
            one of the stream types defined for the cmd object this UI is
            being used with.
        :return: A generator of stream objects. stream objects have a read
            method and a close method which behave as for file objects.
        """
        for stream_spec in self.cmd.input_streams:
            if '*' in stream_spec or '?' in stream_spec or '+' in stream_spec:
                found = stream_type == stream_spec[:-1]
            else:
                found = stream_type == stream_spec
            if found:
                return self._iter_streams(stream_type)
        raise KeyError(stream_type)

    def _iter_streams(self, stream_type):
        """Helper for iter_streams which subclasses should implement."""
        raise NotImplementedError(self._iter_streams)

    def output_error(self, error_tuple):
        """Show an error to the user.

        This is typically used only by Command.execute when run raises an
        exception.

        :param error_tuple: An error tuple obtained from sys.exc_info().
        """
        raise NotImplementedError(self.output_error)

    def output_log(self, level, section, line):
        """Show a log message.

        This is used to show some unstructured text, which may go to a log file
        on disk, the console, a trace window or whatever. 

        :param level: How important the message is to show. 1 is not at all
            urgent, 9 is as urgent as it gets. Most UI's will show 5 and above
            by default. The CLI UI logs levels 8 and 9 only to
            ~/.cache/lmirror/log.
        :param section: A free text string for categorisation, can be used by
            UI's to do per-section levels (but none do so today).
        :param line: A line to log.
        """
        raise NotImplementedError(self.output_log)

    def output_rest(self, rest_string):
        """Show rest_string - a ReST document.

        This is typically used as the entire output for command help or
        documentation.
        
        :param rest_string: A ReST source to display.
        """
        raise NotImplementedError(self.output_rest)

    def output_stream(self, stream):
        """Show a byte stream to the user.

        This is not currently typed, but in future a MIME type may be
        permitted.

        :param stream: A file like object that can be read from. The UI will
        not close the file.
        """
        raise NotImplementedError(self.output_stream)

    def output_table(self, table):
        """Show a table to the user.

        :param table: an iterable of rows. The first row is used for column
            headings, and every row needs the same number of cells.
            e.g. output_table([('name', 'age'), ('robert', 1234)])
        """
        raise NotImplementedError(self.output_table)

    def output_values(self, values):
        """Show values to the user.

        :param values: An iterable of (label, value).
        """
        raise NotImplementedError(self.output_values)

    def set_command(self, cmd):
        """Inform the UI what command it is running.

        This is used to gather command line arguments, or prepare dialogs and
        otherwise ensure that the information the command has declared it needs
        will be available. The default implementation simply sets self.cmd to
        cmd.
        
        :param cmd: A l_mirror.commands.Command.
        """
        self.cmd = cmd
        return self._check_cmd()

    def subprocess_Popen(self, *args, **kwargs):
        """Call an external process from the UI's context.
        
        The behaviour of this call should match the Popen process on any given
        platform, except that the UI can take care of any wrapping or
        manipulation needed to fit into its environment.
        """
        # This might not be the right place.
        raise NotImplementedError(self.subprocess_Popen)
