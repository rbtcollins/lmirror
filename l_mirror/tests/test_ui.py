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

"""Tests for UI support logic and the UI contract."""

from cStringIO import StringIO
import optparse
import subprocess
import sys

from l_mirror import arguments, commands
import l_mirror.arguments.command
from l_mirror.commands import commands as cmd_commands
from l_mirror.ui import cli, model
from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.logging_resource import LoggingResourceManager
from l_mirror.tests.stubhome import StubHomeResource


def cli_ui_factory(input_streams=None, options=(), args=()):
    if input_streams and len(input_streams) > 1:
        # TODO: turn additional streams into argv and simulated files, or
        # something - however, may need to be cli specific tests at that
        # point.
        raise NotImplementedError(cli_ui_factory)
    stdout = StringIO()
    if input_streams:
        stdin = StringIO(input_streams[0][1])
    else:
        stdin = StringIO()
    stderr = StringIO()
    argv = list(args)
    for option, value in options:
        # only bool handled so far
        if value:
            argv.append('--%s' % option)
    return cli.UI(argv, stdin, stdout, stderr, no_logfile=True)


# what ui implementations do we need to test?
ui_implementations = [
    ('CLIUI', {'ui_factory': cli_ui_factory,
        'resources':[('logging', LoggingResourceManager())]}),
    ('ModelUI', {'ui_factory': model.UI}),
    ]


class TestUIContract(ResourcedTestCase):

    scenarios = ui_implementations

    def get_test_ui(self):
        ui = self.ui_factory()
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        return ui

    def test_factory_noargs(self):
        ui = self.ui_factory()

    def test_factory_input_stream_args(self):
        ui = self.ui_factory([('subunit', 'value')])

    def test_here(self):
        ui = self.get_test_ui()
        self.assertNotEqual(None, ui.here)

    def test_iter_streams_load_stdin_use_case(self):
        # A UI can be asked for the streams that a command has indicated it
        # accepts, which is what load < foo will require.
        ui = self.ui_factory([('subunit', 'test: foo\nsuccess: foo\n')])
        cmd = commands.Command(ui)
        cmd.input_streams = ['subunit+']
        ui.set_command(cmd)
        results = []
        for result in ui.iter_streams('subunit'):
            results.append(result.read())
        self.assertEqual(['test: foo\nsuccess: foo\n'], results)

    def test_iter_streams_unexpected_type_raises(self):
        ui = self.get_test_ui()
        self.assertRaises(KeyError, ui.iter_streams, 'subunit')

    def test_output_error(self):
        try:
            raise Exception('fooo')
        except Exception:
            err_tuple = sys.exc_info()
        ui = self.get_test_ui()
        ui.output_error(err_tuple)

    def test_output_log(self):
        # output a log message - plain text with no particular structure
        ui = self.get_test_ui()
        ui.output_log(0, 'my.section', 'message')

    def test_output_rest(self):
        # output some ReST - used for help and docs.
        ui = self.get_test_ui()
        ui.output_rest('')

    def test_output_stream(self):
        # a stream of bytes can be output.
        ui = self.get_test_ui()
        ui.output_stream(StringIO())

    def test_output_table(self):
        # output_table shows a table.
        ui = self.get_test_ui()
        ui.output_table([('col1', 'col2'), ('row1c1','row1c2')])
        
    def test_output_values(self):
        # output_values can be called and takes a list of things to output.
        ui = self.get_test_ui()
        ui.output_values([('foo', 1), ('bar', 'quux')])

    def test_set_command(self):
        # All ui objects can be given their command.
        ui = self.ui_factory()
        cmd = commands.Command(ui)
        self.assertEqual(True, ui.set_command(cmd))

    def test_set_command_checks_args_unwanted_arg(self):
        ui = self.ui_factory(args=['foo'])
        cmd = commands.Command(ui)
        self.assertEqual(False, ui.set_command(cmd))

    def test_set_command_checks_args_missing_arg(self):
        ui = self.ui_factory()
        cmd = commands.Command(ui)
        cmd.args = [arguments.command.CommandArgument('foo')]
        self.assertEqual(False, ui.set_command(cmd))

    def test_set_command_checks_args_invalid_arg(self):
        ui = self.ui_factory(args=['a'])
        cmd = commands.Command(ui)
        cmd.args = [arguments.command.CommandArgument('foo')]
        self.assertEqual(False, ui.set_command(cmd))

    def test_args_are_exposed_at_arguments(self):
        ui = self.ui_factory(args=['commands'])
        cmd = commands.Command(ui)
        cmd.args = [arguments.command.CommandArgument('commands')]
        self.assertEqual(True, ui.set_command(cmd))
        self.assertEqual({'commands':[cmd_commands.commands]}, ui.arguments)

    def test_options_at_options(self):
        ui = self.get_test_ui()
        self.assertEqual(False, ui.options.quiet)

    def test_options_when_set_at_options(self):
        ui = self.ui_factory(options=[('quiet', True)])
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        self.assertEqual(True, ui.options.quiet)

    def test_options_on_command_picked_up(self):
        ui = self.ui_factory(options=[('subunit', True)])
        cmd = commands.Command(ui)
        cmd.options = [optparse.Option("--subunit", action="store_true",
            default=False, help="Show output as a subunit stream.")]
        ui.set_command(cmd)
        self.assertEqual(True, ui.options.subunit)
        # And when not given the default works.
        ui = self.ui_factory()
        cmd = commands.Command(ui)
        cmd.options = [optparse.Option("--subunit", action="store_true",
            default=False, help="Show output as a subunit stream.")]
        ui.set_command(cmd)
        self.assertEqual(False, ui.options.subunit)

    def test_exec_subprocess(self):
        # exec_subprocess should 'work like popen'.
        ui = self.ui_factory()
        proc = ui.subprocess_Popen('ls', stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out, err = proc.communicate()
        proc.returncode
