__all__ = ['BaseStep', 'SyncStep', 'BaseSaga', 'NO_ACTION']

import logging
import typing
from abc import ABC
from dataclasses import asdict

from .utils import serialize_saga_error, \
    format_exception_as_python_does, NO_ACTION

logger = logging.getLogger(__name__)


class BaseStep(ABC):
    def __init__(self,
                 name: str,
                 action: typing.Callable = NO_ACTION,
                 compensation: typing.Callable = NO_ACTION,
                 ):
        self.name = name
        self.action = action
        self.compensation = compensation


class SyncStep(BaseStep):
    pass


class BaseSaga:
    saga_id: int = None
    steps: typing.List[BaseStep] = None

    def __init__(self, saga_id: int):
        self.saga_id = saga_id

    def get_first_step(self) -> BaseStep:
        return self.steps[0]

    def get_step_by_name(self, step_name: str) -> BaseStep:
        for step in self.steps:
            if step.name == step_name:
                return step

        raise KeyError(f'no step found with name {step_name}')

    def _get_step_index(self, step: BaseStep) -> int:
        for i in range(len(self.steps)):
            if self.steps[i].name == step.name:
                return i

        raise IndexError(f'step wasn\'t found')

    def _get_next_step(self, step: typing.Union[BaseStep, None]) -> typing.Union[BaseStep, None]:
        if not step:
            return self.steps[0]

        step_index = self._get_step_index(step)

        its_last_step = (step_index == len(self.steps) - 1)

        if its_last_step:
            return None
        else:
            return self.steps[step_index + 1]

    def _get_previous_step(self, step: typing.Union[BaseStep, None]) -> typing.Union[BaseStep, None]:
        step_index = self._get_step_index(step)

        its_first_step = (step_index == 0)

        if its_first_step:
            return None
        else:
            return self.steps[step_index - 1]

    def step_is_last(self, step: BaseStep):
        return step == self.steps[-1]

    def run_step(self, step: BaseStep):
        logger.info(f'Saga {self.saga_id}: running "{step.name}" step')
        step.action(step)

    def compensate_step(self, step: BaseStep, initial_failure_payload: dict):
        logger.info(f'Saga {self.saga_id}: '
                    f'compensating "{step.name}" step')
        step.compensation(step)

    def compensate(self, failed_step: BaseStep, initial_failure_payload: dict = None):
        try:
            step = self._get_previous_step(failed_step)
            while step:
                self.compensate_step(step, initial_failure_payload)
                step = self._get_previous_step(step)

            self.on_saga_failure(failed_step, initial_failure_payload)

        except BaseException as exception:
            self.on_compensation_failure(
                initially_failed_step=failed_step,
                initial_failure_payload=initial_failure_payload,
                compensation_failed_step=failed_step,
                compensation_exception=exception
            )

    def execute(self, starting_step: BaseStep = None):
        if starting_step is None:
            starting_step = self.steps[0]

        step = starting_step
        need_to_run_next_step = True
        exception = None

        while step and need_to_run_next_step:
            # noinspection PyBroadException
            try:
                self.run_step(step)

            except BaseException as exc:
                exception = exc
                break

            # After running a step, we will run next one if current step was sync
            # For AsyncStep's, we firstly wait for on_success event from step handlers
            #  and only then continue saga (see on_async_step_success method)
            need_to_run_next_step = isinstance(step, SyncStep)
            if need_to_run_next_step:
                step = self._get_next_step(step)

        # if error occured, compensate saga
        if exception:
            self.compensate(
                step,
                initial_failure_payload=asdict(serialize_saga_error(exception))
            )
        # if we ended on a last step, run on_saga_success
        elif step is None:
            self.on_saga_success()

    def on_saga_success(self):
        """
        This method runs when saga is fully completed with success
        """

        logger.info(f'Saga {self.saga_id} succeeded')

    def on_saga_failure(self, failed_step: BaseStep, initial_failure_payload: dict):
        """
        This method runs when saga is failed (after all compensations finished)
        """
        logger.info(f'Saga {self.saga_id} failed on "{failed_step.name}" step. \n'
                    f'Failure details: {initial_failure_payload}')

    def on_compensation_failure(self, initially_failed_step: BaseStep,
                                initial_failure_payload: dict,
                                compensation_failed_step: BaseStep,
                                compensation_exception: BaseException):
        """
        This method runs when compensation step unexpectedly failed,
          i.e. saga wasn't able to successfully rollback
        """
        logger.info(f'Saga {self.saga_id} failed while compensating "{compensation_failed_step.name}" step.\n'
                    f'Error details: {format_exception_as_python_does(compensation_exception)} \n \n'
                    f'Initial failure details: {initial_failure_payload}')

