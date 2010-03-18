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

"""Tests for the commands module."""

import os.path
import sys

from testresources import TestResource

from l_mirror import commands
from l_mirror.tests import ResourcedTestCase
from l_mirror.tests.matchers import MatchesException
from l_mirror.tests.stubpackage import (
    StubPackageResource,
    )
from l_mirror.ui import cli, model


class TemporaryCommand(object):
    """A temporary command."""


class TemporaryCommandResource(TestResource):

    def __init__(self, cmd_name):
        TestResource.__init__(self)
        self.resources.append(('pkg',
            StubPackageResource('commands',
            [('%s.py' % cmd_name,
             """from l_mirror.commands import Command
class %s(Command):
    def run(self):
        pass
""" % cmd_name)], init=False)))
        self.cmd_name = cmd_name

    def make(self, dependency_resources):
        pkg = dependency_resources['pkg']
        result = TemporaryCommand()
        result.path = os.path.join(pkg.base, 'commands')
        commands.__path__.append(result.path)
        return result

    def clean(self, resource):
        commands.__path__.remove(resource.path)
        name = 'l_mirror.commands.%s' % self.cmd_name
        if name in sys.modules:
            del sys.modules[name]


class TestFindCommand(ResourcedTestCase):

    resources = [('cmd', TemporaryCommandResource('foo'))]

    def test_looksupcommand(self):
        cmd = commands._find_command('foo')
        self.assertIsInstance(cmd(None), commands.Command)

    def test_missing_command(self):
        self.assertRaises(KeyError, commands._find_command, 'bar')

    def test_sets_name(self):
        cmd = commands._find_command('foo')
        self.assertEqual('foo', cmd.name)


class TestFindHyphenCommand(ResourcedTestCase):

    resources = [('cmd', TemporaryCommandResource('foo_bar'))]

    def test_looksupcommand_hypen(self):
        cmd = commands._find_command('foo-bar')
        self.assertIsInstance(cmd(None), commands.Command)


class TestIterCommands(ResourcedTestCase):

    resources = [
        ('cmd1', TemporaryCommandResource('one')),
        ('cmd2', TemporaryCommandResource('two')),
        ]

    def test_iter_commands(self):
        cmds = list(commands.iter_commands())
        cmds = [cmd(None).name for cmd in cmds]
        # We don't care about all the built in commands
        cmds = [cmd for cmd in cmds if cmd in ('one', 'two')]
        self.assertEqual(['one', 'two'], cmds)


class InstrumentedCommand(commands.Command):
    """A command which records methods called on it.
    
    The first line is the summary.
    """

    def _init(self):
        self.calls = []

    def execute(self):
        self.calls.append('execute')
        return commands.Command.execute(self)

    def run(self):
        self.calls.append('run')


class TestAbstractCommand(ResourcedTestCase):

    def test_execute_calls_run(self):
        cmd = InstrumentedCommand(model.UI())
        self.assertEqual(0, cmd.execute())
        self.assertEqual(['execute', 'run'], cmd.calls)

    def test_execute_calls_set_command(self):
        ui = model.UI()
        cmd = InstrumentedCommand(ui)
        cmd.execute()
        self.assertEqual(cmd, ui.cmd)

    def test_execute_does_not_run_if_set_command_errors(self):
        class FailUI(object):
            def set_command(self, ui):
                return False
        cmd = InstrumentedCommand(FailUI())
        self.assertEqual(1, cmd.execute())

    def test_shows_errors_from_execute_returns_3(self):
        class FailCommand(commands.Command):
            def run(self):
                raise Exception("foo")
        ui = model.UI()
        cmd = FailCommand(ui)
        self.assertEqual(3, cmd.execute())
        self.assertEqual(1, len(ui.outputs))
        self.assertEqual('error', ui.outputs[0][0])
        self.assertThat(ui.outputs[0][1], MatchesException(Exception('foo')))

    def test_get_summary(self):
        cmd = InstrumentedCommand
        self.assertEqual('A command which records methods called on it.',
            cmd.get_summary())
