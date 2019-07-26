#!/usr/bin/env python

# Copyright (c) 2019 Orange and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0

"""Define the classes required to fully cover behave."""

import logging
import unittest

import mock
from xtesting.core import behaveframework

__author__ = "Deepak Chandella <deepak.chandella@orange.com>"


class ParseResultTesting(unittest.TestCase):

    """The class testing BehaveFramework.parse_results()."""
    # pylint: disable=missing-docstring

    _response = [{'status': 'passed'}]

    def setUp(self):
        self.test = behaveframework.BehaveFramework(
            case_name='behave', project_name='xtesting')

    def test_raises_exc_open(self):
        self.test.json_file = 'dummy_file'
        self.test.response = self._response
        with mock.patch('six.moves.builtins.open',
                        mock.mock_open()) as mock_file:
            mock_file.side_effect = IOError()
            self.assertRaises(IOError, self.test.parse_results())
        mock_file.assert_called_once_with('dummy_file')

    def test_raises_exc_key(self):
        with mock.patch('six.moves.builtins.open', mock.mock_open()), \
                mock.patch('json.load', return_value=[{'foo': 'bar'}]):
            self.assertRaises(KeyError, self.test.parse_results())

    def test_raises_exe_zerodivision(self):
        with mock.patch('six.moves.builtins.open', mock.mock_open()), \
                mock.patch('json.load', mock.Mock(return_value=[])):
            self.assertRaises(ZeroDivisionError, self.test.parse_results())

    def _test_result(self, response, result):
        with mock.patch('six.moves.builtins.open', mock.mock_open()), \
                mock.patch('json.load', mock.Mock(return_value=response)):
            self.test.parse_results()
            self.assertEqual(self.test.result, result)

    def test_null_passed(self):
        data = [{'status': 'dummy'}]
        self._test_result(data, 0)

    def test_half_success(self):
        data = [{'status': 'passed'}, {'status': 'failed'}]
        self._test_result(data, 50)

    def test_success(self):
        data = [{'status': 'passed'}, {'status': 'passed'}]
        self._test_result(data, 100)

    @mock.patch('six.moves.builtins.open', mock.mock_open())
    def test_count(self, *args):  # pylint: disable=unused-argument
        self._response.extend([{'status': 'failed'}, {'status': 'skipped'}])
        with mock.patch('json.load', mock.Mock(return_value=self._response)):
            self.test.parse_results()
            self.assertEqual(self.test.details['pass_tests'], 1)
            self.assertEqual(self.test.details['fail_tests'], 1)
            self.assertEqual(self.test.details['skip_tests'], 1)
            self.assertEqual(self.test.details['total_tests'], 3)


class RunTesting(unittest.TestCase):

    """The class testing BehaveFramework.run()."""
    # pylint: disable=missing-docstring

    suites = ["foo"]
    tags = []

    def setUp(self):
        self.test = behaveframework.BehaveFramework(
            case_name='behave', project_name='xtesting')

    def test_exc_key_error(self):
        self.assertEqual(self.test.run(), self.test.EX_RUN_ERROR)

    @mock.patch('xtesting.core.behaveframework.behave_main')
    def _test_makedirs_exc(self, *args):
        with mock.patch.object(self.test, 'parse_results') as mock_method:
            self.assertEqual(
                self.test.run(
                    suites=self.suites, tags=self.tags),
                self.test.EX_RUN_ERROR)
            args[0].assert_not_called()
            mock_method.asser_not_called()

    @mock.patch('os.makedirs', side_effect=Exception)
    @mock.patch('os.path.exists', return_value=False)
    def test_makedirs_exc(self, *args):
        self._test_makedirs_exc()
        args[0].assert_called_once_with(self.test.res_dir)
        args[1].assert_called_once_with(self.test.res_dir)

    @mock.patch('xtesting.core.behaveframework.behave_main')
    def _test_makedirs(self, *args):
        with mock.patch.object(self.test, 'parse_results') as mock_method:
            self.assertEqual(
                self.test.run(suites=self.suites, tags=self.tags),
                self.test.EX_OK)
            args[0].assert_called_once_with(
                ['--tags=',
                 '--format=json',
                 '--outfile={}'.format(self.test.json_file),
                 'foo'])
            mock_method.assert_called_once_with()

    @mock.patch('os.makedirs')
    @mock.patch('os.path.exists', return_value=False)
    def test_makedirs(self, *args):
        self._test_makedirs()
        args[0].assert_called_once_with(self.test.res_dir)
        args[1].assert_called_once_with(self.test.res_dir)

    @mock.patch('os.makedirs')
    @mock.patch('os.path.exists', return_value=True)
    def test_makedirs_oserror17(self, *args):
        self._test_makedirs()
        args[0].assert_called_once_with(self.test.res_dir)
        args[1].assert_not_called()

    @mock.patch('os.makedirs')
    @mock.patch('xtesting.core.behaveframework.behave_main')
    def _test_parse_results(self, status, *args):
        self.assertEqual(
            self.test.run(
                suites=self.suites, tags=self.tags),
            status)
        args[0].assert_called_once_with(
            ['--tags=',
             '--format=json',
             '--outfile={}'.format(self.test.json_file),
             'foo'])
        args[1].assert_called_once_with(self.test.res_dir)

    def test_parse_results_exc(self):
        with mock.patch.object(self.test, 'parse_results',
                               side_effect=Exception) as mock_method:
            self._test_parse_results(self.test.EX_RUN_ERROR)
            mock_method.assert_called_once_with()

if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    unittest.main(verbosity=2)
