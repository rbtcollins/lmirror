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

"""Am object based UI for l_mirror."""

from cStringIO import StringIO
import optparse

from l_mirror import ui

class ProcessModel(object):
    """A subprocess.Popen test double."""

    def __init__(self, ui):
        self.ui = ui
        self.returncode = 0

    def communicate(self):
        self.ui.outputs.append(('communicate',))
        return '', ''


class UI(ui.AbstractUI):
    """A object based UI.
    
    This is useful for reusing the Command objects that provide a simplified
    interaction model with the domain logic from python. It is used for
    testing l_mirror commands.
    """

    def __init__(self, input_streams=None, options=(), args=(), log_level=4):
        """Create a model UI.

        :param input_streams: A list of stream name, bytes stream tuples to be
            used as the available input streams for this ui.
        :param options: Options to explicitly set values for. A list of
            (option, value) items.
        :param args: The argument values to give the UI.
        :param log_level: Log level to filter on by default.
        """
        self.input_streams = {}
        if input_streams:
            for stream_type, stream_bytes in input_streams:
                self.input_streams.setdefault(stream_type, []).append(
                    stream_bytes)
        self.here = 'memory:'
        self.unparsed_opts = options
        self.outputs = []
        # Could take parsed args, but for now this is easier.
        self.unparsed_args = args
        self.log_level = log_level

    def _check_cmd(self):
        options = list(self.unparsed_opts)
        self.options = optparse.Values()
        seen_options = set()
        for option, value in options:
            setattr(self.options, option, value)
            seen_options.add(option)
        if not 'quiet' in seen_options:
            setattr(self.options, 'quiet', False)
        for option in self.cmd.options:
            if not option.dest in seen_options:
                setattr(self.options, option.dest, option.default)
        args = list(self.unparsed_args)
        parsed_args = {}
        failed = False
        for arg in self.cmd.args:
            try:
                parsed_args[arg.name] = arg.parse(args)
            except ValueError:
                failed = True
                break
        self.arguments = parsed_args
        return args == [] and not failed

    def _iter_streams(self, stream_type):
        streams = self.input_streams.pop(stream_type, [])
        for stream_bytes in streams:
            yield StringIO(stream_bytes)

    def output_error(self, error_tuple):
        self.outputs.append(('error', error_tuple))

    def output_log(self, level, section, line):
        if level > self.log_level:
            self.outputs.append(('log', level, section, line))

    def output_rest(self, rest_string):
        self.outputs.append(('rest', rest_string))

    def output_stream(self, stream):
        self.outputs.append(('stream', stream.read()))

    def output_table(self, table):
        self.outputs.append(('table', table))

    def output_values(self, values):
        self.outputs.append(('values', values))

    def subprocess_Popen(self, *args, **kwargs):
        # Really not an output - outputs should be renamed to events.
        self.outputs.append(('popen', args, kwargs))
        return ProcessModel(self)
