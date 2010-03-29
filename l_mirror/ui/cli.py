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

"""A command line UI for l_mirror."""

__all__ = ['UI', 'run_argv']

import logging
from optparse import OptionParser
import os
import sys

from l_mirror import commands, ui
from l_mirror import logging_support


class UI(ui.AbstractUI):
    """A command line user interface."""

    def __init__(self, argv, stdin, stdout, stderr, no_logfile=False):
        """Create a command line UI.

        This UI logs to ~/.cache/lmirror/log for level 3 and up by default,
        and level 5 and up to the console.

        :param argv: Arguments from the process invocation.
        :param stdin: The stream for stdin.
        :param stdout: The stream for stdout.
        :param stderr: The stream for stderr.
        ;param no_logfile: Disable default ~/.cache/lmirror/log logfile.
        """
        self._argv = argv
        self._stdin = stdin
        self._stdout = stdout
        self._stderr = stderr
        if no_logfile:
            args = [None]
        else:
            args = []
        self._c_log, self._f_log, self._log_formatter = \
            logging_support.configure_logging(self._stdout, *args)
        self._c_log.setLevel(5)
        if self._f_log is not None:
            self._f_log.setLevel(3) # log more than the UI, but not everything.

    def _iter_streams(self, stream_type):
        yield self._stdin

    def output_error(self, error_tuple):
        self._stderr.write(str(error_tuple[1]) + '\n')
        logging.getLogger().log(3, "Error", exc_info=1)

    def output_log(self, level, section, line):
        logger = logging.getLogger(section)
        logger.log(level, line)

    def output_rest(self, rest_string):
        self._stdout.write(rest_string)
        if not rest_string.endswith('\n'):
            self._stdout.write('\n')

    def output_stream(self, stream):
        contents = stream.read(65536)
        while contents:
            self._stdout.write(contents)
            contents = stream.read(65536)

    def output_table(self, table):
        # stringify
        contents = []
        for row in table:
            new_row = []
            for column in row:
                new_row.append(str(column))
            contents.append(new_row)
        if not contents:
            return
        widths = [0] * len(contents[0])
        for row in contents:
            for idx, column in enumerate(row):
                if widths[idx] < len(column):
                    widths[idx] = len(column)
        # Show a row
        outputs = []
        def show_row(row):
            for idx, column in enumerate(row):
                outputs.append(column)
                if idx == len(row) - 1:
                    outputs.append('\n')
                    return
                # spacers for the next column
                outputs.append(' '*(widths[idx]-len(column)))
                outputs.append('  ')
        show_row(contents[0])
        # title spacer
        for idx, width in enumerate(widths):
            outputs.append('-'*width)
            if idx == len(widths) - 1:
                outputs.append('\n')
                continue
            outputs.append('  ')
        for row in contents[1:]:
            show_row(row)
        self._stdout.write(''.join(outputs))

    def output_values(self, values):
        outputs = []
        for label, value in values:
            outputs.append('%s: %s' % (label, value))
        self._stdout.write('%s\n' % ' '.join(outputs))

    def _check_cmd(self):
        cmd = self.cmd
        parser = OptionParser()
        parser.add_option("-d", "--here", dest="here",
            help="Set the directory or url that a command should run from. "
            "This affects all default path lookups but does not affect paths "
            "supplied to the command.", default=os.getcwd(), type=str)
        parser.add_option("-q", "--quiet", action="store_true", default=False,
            help="Turn off output other than the primary output for a command "
            "and any errors.")
        parser.add_option("-v", "--verbose", action="count", dest="verbosity",
            help="Show more detail about program progression on stdout and in "
            "custom log files.")
        for option in self.cmd.options:
            parser.add_option(option)
        options, args = parser.parse_args(self._argv)
        self.here = options.here
        self.options = options
        if self.options.verbosity:
            self._c_log.setLevel(self._c_log.level - self.options.verbosity)
        orig_args = list(args)
        parsed_args = {}
        failed = False
        for arg in self.cmd.args:
            try:
                parsed_args[arg.name] = arg.parse(args)
            except ValueError:
                exc_info = sys.exc_info()
                failed = True
                self._stderr.write("%s\n" % str(exc_info[1]))
                break
        if not failed:
            self.arguments = parsed_args
            if args != []:
                self._stderr.write("Unexpected arguments: %r\n" % args)
        return not failed and args == []

    def subprocess_Popen(self, *args, **kwargs):
        self.output_log(3, 'l_mirror.ui.cli', "Running subprocess %r %r" % (
            args, kwargs))
        import subprocess
        return subprocess.Popen(*args, **kwargs)


def run_argv(argv, stdin, stdout, stderr):
    """Convenience function to run a command with a CLIUI.

    :param argv: The argv to run the command with.
    :param stdin: The stdin stream for the command.
    :param stdout: The stdout stream for the command.
    :param stderr: The stderr stream for the command.
    :return: An integer exit code for the command.
    """
    cmd_name = None
    cmd_args = argv[1:]
    for arg in argv[1:]:
        if not arg.startswith('-'):
            cmd_name = arg
            break
    if cmd_name is None:
        cmd_name = 'help'
        cmd_args = ['help']
    cmd_args.remove(cmd_name)
    cmdclass = commands._find_command(cmd_name)
    ui = UI(cmd_args, stdin, stdout, stderr)
    cmd = cmdclass(ui)
    result = cmd.execute()
    if not result:
        return 0
    return result
