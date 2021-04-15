__all__ = ['saga_step_handler', 'no_response_saga_step_handler',
           'send_saga_response']


import functools
import logging
from dataclasses import dataclass, asdict

import typing

import celery
from celery import Celery, Task

from .utils import success_task_name, failure_task_name, serialize_saga_error

logger = logging.getLogger(__name__)


def send_saga_response(celery_app: Celery,
                       response_task_name: str,
                       response_queue_name: str,
                       saga_id: int,
                       payload):  # assuming payload is a @dataclass
    return celery_app.send_task(
        response_task_name,
        args=[
            saga_id,
            payload
        ],
        queue=response_queue_name
    )


def _saga_step_handler(response_queue: typing.Union[str, None]):
    """
    Apply this decorator between @task and actual task handler.

    @command_handlers_celery_app.task(bind=True, name=verify_consumer_details_message.TASK_NAME)
    @saga_handler(CREATE_ORDER_SAGA_RESPONSE_QUEUE)

    Note: it's important to set bind=True in @task
      because @saga_handler will need access to celery task instance
    """
    def inner(func):
        @functools.wraps(func)
        def wrapper(celery_task: Task, saga_id: int, payload: dict):
            try:
                response_payload = func(celery_task, saga_id, payload)  # type: typing.Union[dict, None]
                # use convention response task name
                task_name = success_task_name(celery_task.name)
            except BaseException as exc:
                # let Celery handle retries
                if isinstance(exc, celery.exceptions.Retry):
                    raise

                logger.exception(exc)

                # serialize error in a unified way
                response_payload = asdict(serialize_saga_error(exc))
                # use convention response task name
                task_name = failure_task_name(celery_task.name)

            if response_queue:
                send_saga_response(celery_task.app,
                                   task_name,
                                   response_queue,
                                   saga_id,
                                   response_payload)
        return wrapper

    return inner


def saga_step_handler(response_queue: str):
    """
    Compensatable saga step assumed.
    For retriable steps, use corresponding decorator

    It's also assumed that you will use this decorator with
     @task decorator, see docstring for _saga_step_handler
    """
    return _saga_step_handler(response_queue)


no_response_saga_step_handler = _saga_step_handler(response_queue=None)
"""
It's assumed that you will use this decorator with
 @task decorator, see docstring for _saga_step_handler
"""


