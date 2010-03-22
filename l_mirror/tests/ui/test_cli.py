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

import doctest
from cStringIO import StringIO
import sys

from testtools.matchers import DocTestMatches

from l_mirror import arguments
import l_mirror.arguments.command
import l_mirror.arguments.string
from l_mirror import commands
from l_mirror.ui import cli
from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.logging_resource import LoggingResourceManager
from l_mirror.tests.monkeypatch import monkeypatch
from l_mirror.tests.stubhome import StubHomeResource


class TestCLIUI(ResourcedTestCase):

    resources = [('logging', LoggingResourceManager())]

    def get_test_ui_and_cmd(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr, no_logfile=True)
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_construct(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr, no_logfile=True)

    def test_stream_comes_from_stdin(self):
        stdout = StringIO()
        stdin = StringIO('foo\n')
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr, no_logfile=True)
        cmd = commands.Command(ui)
        cmd.input_streams = ['content']
        ui.set_command(cmd)
        results = []
        for stream in ui.iter_streams('content'):
            results.append(stream.read())
        self.assertEqual(['foo\n'], results)

    def test_dash_d_sets_here_option(self):
        stdout = StringIO()
        stdin = StringIO('foo\n')
        stderr = StringIO()
        ui = cli.UI(['-d', '/nowhere/'], stdin, stdout, stderr, no_logfile=True)
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        self.assertEqual('/nowhere/', ui.here)

    def test_global_option_dash_v_changes_log_level(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI(['-v'], stdin, stdout, stderr, no_logfile=True)
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        self.assertEqual(4, ui._c_log.level)

    def test_outputs_error_string(self):
        try:
            raise Exception('fooo')
        except Exception:
            err_tuple = sys.exc_info()
        expected = str(err_tuple[1]) + '\n'
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr, no_logfile=True)
        ui.output_error(err_tuple)
        self.assertThat(stderr.getvalue(), DocTestMatches(expected))

    def test_outputs_log_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        ui.output_log(5, 'my.self', 'line')
        self.assertThat(ui._stdout.getvalue(),
            DocTestMatches("""line\n""", doctest.ELLIPSIS))

    def test_outputs_rest_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        ui.output_rest('topic\n=====\n')
        self.assertEqual('topic\n=====\n', ui._stdout.getvalue())

    def test_outputs_stream_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        stream = StringIO("Foo \n bar")
        ui.output_stream(stream)
        self.assertEqual("Foo \n bar", ui._stdout.getvalue())

    def test_outputs_tables_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        ui.output_table([('foo', 1), ('b', 'quux')])
        self.assertEqual('foo  1\n---  ----\nb    quux\n',
            ui._stdout.getvalue())

    def test_outputs_values_to_stdout(self):
        ui, cmd = self.get_test_ui_and_cmd()
        ui.output_values([('foo', 1), ('bar', 'quux')])
        self.assertEqual('foo: 1 bar: quux\n', ui._stdout.getvalue())

    def test_parse_error_goes_to_stderr(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI(['one'], stdin, stdout, stderr, no_logfile=True)
        cmd = commands.Command(ui)
        cmd.args = [arguments.command.CommandArgument('foo')]
        ui.set_command(cmd)
        self.assertEqual("Could not find command 'one'.\n", stderr.getvalue())

    def test_parse_excess_goes_to_stderr(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI(['one'], stdin, stdout, stderr, no_logfile=True)
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        self.assertEqual("Unexpected arguments: ['one']\n", stderr.getvalue())

    def test_parse_after_double_dash_are_arguments(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI(['one', '--', '--two', 'three'], stdin, stdout, stderr,
            no_logfile=True)
        cmd = commands.Command(ui)
        cmd.args = [arguments.string.StringArgument('args', max=None)]
        ui.set_command(cmd)
        self.assertEqual({'args':['one', '--two', 'three']}, ui.arguments)


class TestRunArgv(ResourcedTestCase):

    def stub__find_command(self, cmd_run):
        self.calls = []
        self.addCleanup(monkeypatch('l_mirror.commands._find_command',
            self._find_command))
        self.cmd_run = cmd_run

    def _find_command(self, cmd_name):
        self.calls.append(cmd_name)
        real_run = self.cmd_run
        class SampleCommand(commands.Command):
            """A command that is used for testing."""
            def execute(self):
                return real_run(self)
        return SampleCommand

    def test_looks_up_cmd(self):
        self.stub__find_command(lambda x:0)
        cli.run_argv(['lmirror', 'foo'], 'in', 'out', 'err')
        self.assertEqual(['foo'], self.calls)

    def test_looks_up_cmd_skips_options(self):
        self.stub__find_command(lambda x:0)
        cli.run_argv(['lmirror', '--version', 'foo'], 'in', 'out', 'err')
        self.assertEqual(['foo'], self.calls)

    def test_no_cmd_issues_help(self):
        self.stub__find_command(lambda x:0)
        cli.run_argv(['lmirror', '--version'], 'in', 'out', 'err')
        self.assertEqual(['help'], self.calls)

    def capture_ui(self, cmd):
        self.ui = cmd.ui
        return 0

    def test_runs_cmd_with_CLI_UI(self):
        self.stub__find_command(self.capture_ui)
        cli.run_argv(['lmirror', '--version', 'foo'], 'in', 'out', 'err')
        self.assertEqual(['foo'], self.calls)
        self.assertIsInstance(self.ui, cli.UI)

    def test_returns_0_when_None_returned_from_execute(self):
        self.stub__find_command(lambda x:None)
        self.assertEqual(0, cli.run_argv(['lmirror', 'foo'], 'in', 'out',
            'err'))

    def test_returns_execute_result(self):
        self.stub__find_command(lambda x:1)
        self.assertEqual(1, cli.run_argv(['lmirror', 'foo'], 'in', 'out',
            'err'))


class TestCLILogFile(ResourcedTestCase):

    resources = [('logging', LoggingResourceManager()), 
        ('homedir', StubHomeResource())]

    def get_test_ui_and_cmd(self):
        stdout = StringIO()
        stdin = StringIO()
        stderr = StringIO()
        ui = cli.UI([], stdin, stdout, stderr)
        cmd = commands.Command(ui)
        ui.set_command(cmd)
        return ui, cmd

    def test_outputs_log_to_homedir(self):
        ui, cmd = self.get_test_ui_and_cmd()
        ui.output_log(8, 'my.self', 'line')
        ui.output_log(2, 'my.self', 'not logged line')
        content = file(self.homedir.tempdir + '/.cache/lmirror/log', 'rb').read()
        self.assertThat(content,
            DocTestMatches("""...Z: line\n""", doctest.ELLIPSIS))

