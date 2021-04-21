"""
This module contains AsyncSaga and AsyncSteps which are the very heart
 of saga pattern in microservices.

AsyncSaga includes class methods that allow registering Celery tasks
 that correspond to responses from Saga Handler services

For example, when we send 'create_restaurant_ticket' task to Restaurant service,
 it will respond to message broker with Celery tasks like
   'create_restaurant_ticket.response.success' or
   'create_restaurant_ticket.reesponse.failure'

Saga Orchestrator has its own Celery worker which listen to 'response'
  Celery tasks and launch next step or rollback saga on failure.
See AsyncSaga.register_async_step_handlers for more details.

"""

__all__ = ['AsyncSaga', 'AsyncStep']

import logging
import typing

from celery import Celery, Task

from .base_saga import BaseSaga, BaseStep
from .utils import success_task_name, failure_task_name, NO_ACTION


logger = logging.getLogger(__name__)


class AsyncStep(BaseStep):
    def __init__(self,
                 base_task_name: str,
                 queue: str,
                 on_success: typing.Callable = NO_ACTION,
                 on_failure: typing.Callable = NO_ACTION,
                 *args, **kwargs
                 ):
        self.base_task_name = base_task_name
        self.queue = queue
        self.on_success = on_success
        self.on_failure = on_failure

        super().__init__(*args, **kwargs)


class AsyncSaga(BaseSaga):
    """
    Saga that has integration with Celery
    """
    celery_app: Celery = None

    def __init__(self, celery_app: Celery, *args, **kwargs):
        self.celery_app = celery_app
        super().__init__(*args, **kwargs)

    def on_async_step_success(self, step: AsyncStep, payload: dict):
        logger.info(f'Saga {self.saga_id}: '
                    f'running on_success for "{step.name}" step')

        step.on_success(step, payload)

        if self.step_is_last(step):
            self.on_saga_success()
        else:
            next_step = self._get_next_step(step)
            self.execute(next_step)

    def on_async_step_failure(self, step: AsyncStep, payload: dict):
        logger.info(f'Saga {self.saga_id}: '
                    f'running on_failure for "{step.name}" step')

        step.on_failure(step, payload)
        self.compensate(step, payload)

    @property
    def async_steps(self) -> typing.List[AsyncStep]:
        return [step for step in self.steps if isinstance(step, AsyncStep)]

    def get_async_step_by_success_task_name(self, success_task_name_: str) -> AsyncStep:
        for step in self.async_steps:
            if success_task_name(step.base_task_name) == success_task_name_:
                return step

        raise KeyError(f'no step found with success task name {success_task_name_}')

    def get_async_step_by_failure_task_name(self, failure_task_name_: str) -> AsyncStep:
        for step in self.async_steps:
            if failure_task_name(step.base_task_name) == failure_task_name_:
                return step

        raise KeyError(f'no step found with failure task name {failure_task_name_}')

    @classmethod
    def register_async_step_handlers(cls, celery_app: Celery):
        # noinspection PyTypeChecker
        dummy_saga_instance = cls(None, None)

        for step in dummy_saga_instance.async_steps:
            cls.register_success_handler_for_step(celery_app, step)
            cls.register_failure_handler_for_step(celery_app, step)

    @classmethod
    def register_success_handler_for_step(cls, celery_app: Celery, step: AsyncStep):
        def on_success_handler(celery_task: Task, saga_id: int, payload: dict):
            saga = cls(celery_app=celery_app, saga_id=saga_id)

            step_ = saga.get_async_step_by_success_task_name(celery_task.name)
            saga.on_async_step_success(step_, payload)

        celery_app.task(
            name=success_task_name(step.base_task_name),
            bind=True
        )(on_success_handler)

    @classmethod
    def register_failure_handler_for_step(cls, celery_app: Celery, step: AsyncStep):

        def on_failure_handler(celery_task: Task, saga_id: int, payload: dict):
            saga = cls(celery_app, saga_id)

            step_ = saga.get_async_step_by_failure_task_name(celery_task.name)
            saga.on_async_step_failure(step_, payload)

        celery_app.task(
            name=failure_task_name(step.base_task_name),
            bind=True
        )(on_failure_handler)

    def send_message_to_other_service(self, step: AsyncStep, payload: dict, task_name: str = None):
        """
        Helper for sending Celery tasks to Async Handler Services
        """
        task_result = self.celery_app.send_task(
            task_name or step.base_task_name,
            args=[
                self.saga_id,
                payload
            ],
            queue=step.queue
        )

        return task_result.id
