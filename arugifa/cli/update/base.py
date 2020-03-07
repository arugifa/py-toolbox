"""Base classes to manage updates."""

import sys
from abc import ABC, abstractmethod, abstractproperty
from contextlib import contextmanager
from io import StringIO
from typing import Any, TextIO

from tqdm import tqdm

from arugifa.cli.update import exceptions
from arugifa.cli.update.input import Prompt
from arugifa.cli.update.typing import (
    UpdateErrors, UpdateProgress, UpdateTodo, UpdateResult)


class BaseUpdatePlanFailure(ABC, exceptions.UpdateError):
    def __init__(self, errors: UpdateErrors):
        self.errors = errors

    @abstractmethod
    def __str__(self):
        pass


class BaseUpdateRunFailure(ABC, exceptions.UpdateError):
    def __init__(self, errors: UpdateErrors):
        self.errors = errors

    @abstractmethod
    def __str__(self):
        pass


class BaseUpdateRunner(ABC):

    def __init__(
            self, manager: Any, *,
            prompt: 'Prompt' = None, output: TextIO = sys.stdout,
            show_progress: bool = True):

        self.manager = manager
        self.prompt = prompt or Prompt(output=output)
        self.output = output
        self.show_progress = show_progress

    # Abstract Attributes

    @abstractproperty
    def preview(self) -> str:
        pass

    @abstractproperty
    def report(self) -> str:
        pass

    @abstractmethod
    async def _plan(self) -> UpdateTodo:
        """:raise BaseUpdatePlanFailure: ..."""
        pass

    @abstractmethod
    async def _run(self) -> UpdateResult:
        """:raise BaseUpdateRunFailure: ..."""

    # Properties

    @property
    def progress(self) -> UpdateProgress:
        return self._progress

    @property
    def result(self) -> UpdateResult:
        if not self._result:
            raise exceptions.UpdateNotRun

        return self._result

    @property
    def todo(self) -> UpdateTodo:
        if not self._todo:
            raise exceptions.UpdateNotPlanned

        return self._todo

    # Main API

    def confirm(self) -> None:
        try:
            self.prompt.confirm()
        except AssertionError:
            raise exceptions.UpdateAborted()

    async def plan(self, *, show_preview: bool = False) -> UpdateTodo:
        """:raise BaseUpdatePlanFailure: xxx"""
        self._todo = await self._plan()  # Can raise BaseUpdatePlanFailure

        if show_preview:
            print(self.preview, file=self.output)

        return self._todo

    async def run(self, *, show_report: bool = False) -> UpdateResult:
        """:raise BaseUpdateRunFailure: xxx"""
        self._result = await self._run()  # Can raise BaseUpdateRunFailure

        if show_report:
            print(self.report, file=self.output)

        return self._result

    @contextmanager
    def progress_bar(self, *, total: int) -> None:
        output = self.output if self.show_progress else StringIO()

        try:
            with tqdm(total=total, file=output) as pbar:
                self._progress = pbar
                yield
        finally:
            self._progress = None
