#!/usr/bin/env python

# Copyright (c) 2016 ZTE Corp and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0

"""Define the parent classes of all Xtesting Features.

Feature is considered as TestCase offered by Third-party. It offers
helpers to run any python method or any bash command.
"""

import abc
import logging
import os
import subprocess
import sys
import time

from xtesting.core import testcase

__author__ = ("Serena Feng <feng.xiaowei@zte.com.cn>, "
              "Cedric Ollivier <cedric.ollivier@orange.com>")


class Feature(testcase.TestCase, metaclass=abc.ABCMeta):
    """Base model for single feature."""

    __logger = logging.getLogger(__name__)

    @abc.abstractmethod
    def execute(self, **kwargs):
        """Execute the Python method.

        The subclasses must override the default implementation which
        is false on purpose.

        The new implementation must return 0 if success or anything
        else if failure.

        Args:
            kwargs: Arbitrary keyword arguments.
        """

    def run(self, **kwargs):
        """Run the feature.

        It allows executing any Python method by calling execute().

        It sets the following attributes required to push the results
        to DB:

            * result,
            * start_time,
            * stop_time.

        It doesn't fulfill details when pushing the results to the DB.

        Args:
            kwargs: Arbitrary keyword arguments.

        Returns:
            TestCase.EX_OK if execute() returns 0,
            TestCase.EX_RUN_ERROR otherwise.
        """
        self.start_time = time.time()
        exit_code = testcase.TestCase.EX_RUN_ERROR
        self.result = 0
        try:
            if self.execute(**kwargs) == 0:
                exit_code = testcase.TestCase.EX_OK
                self.result = 100
        except Exception as e:  # pylint: disable=broad-except
            self.__logger.exception(f"{self.project_name} FAILED, Exception: {e}")
        self.stop_time = time.time()
        return exit_code


class BashFeature(Feature):
    """Class designed to run any bash command."""

    __logger = logging.getLogger(__name__)
    DEFAULT_TIMEOUT = 180  # in seconds

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result_file = f"{self.res_dir}/{self.case_name}.log"

    def execute(self, **kwargs):
        """Execute the cmd passed as arg

        Args:
            kwargs: Arbitrary keyword arguments.

        Returns:
            process return code if no exception,
            -1 otherwise.
        """
        try:
            cmd = kwargs["cmd"]
            console = kwargs["console"] if "console" in kwargs else False
            # For some tests, we may need to force stop after N sec
            max_duration = kwargs.get("max_duration")  # None if not found.
            had_format_error = False
            if max_duration is not None:
                try:
                    max_duration = int(max_duration)
                except (ValueError, TypeError):
                    had_format_error = True
                    self.__logger.info(f'Wrong value for max_duration: "{max_duration}", '
                                       f'defaulting to {self.DEFAULT_TIMEOUT}s.')
                    max_duration = self.DEFAULT_TIMEOUT
            if not os.path.isdir(self.res_dir):
                os.makedirs(self.res_dir)
            with open(self.result_file, 'w', encoding='utf-8') as f_stdout:
                self.__logger.info("Calling %s", cmd)
                if max_duration and not had_format_error:
                    self.__logger.info("Parameter 'max_duration' set to %ss.", max_duration)
                with subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True, encoding="utf-8") as process:
                    try:
                        out, err = process.communicate(timeout=max_duration)
                        if console:
                            sys.stdout.write(out)
                        f_stdout.write(out)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        self.__logger.info(
                            "Killing process after %d second(s).", max_duration)
                        return -2
            with open(self.result_file, 'r', encoding='utf-8') as f_stdin:
                self.__logger.debug("$ %s\n%s", cmd, f_stdin.read().rstrip())
            return process.returncode
        except KeyError:
            self.__logger.error("Please give cmd as arg. kwargs: %s", kwargs)
        return -1
