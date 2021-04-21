__all__ = ['success_task_name', 'failure_task_name', 'SagaErrorPayload',
           'format_exception_as_python_does', 'serialize_saga_error',
           'NO_ACTION']

import traceback
from dataclasses import dataclass


NO_ACTION = lambda *args: None


def success_task_name(task_name: str):
    return f'{task_name}.response.success'


def failure_task_name(task_name: str):
    return f'{task_name}.response.failure'


@dataclass
class SagaErrorPayload:
    type: str
    message: str
    module: str
    traceback: str


def format_exception_as_python_does(e: BaseException):
    # taken from https://stackoverflow.com/a/35498685
    return traceback.format_exception(type(e), e, e.__traceback__)


def serialize_saga_error(exc: BaseException) -> SagaErrorPayload:
    exctype = type(exc)
    return SagaErrorPayload(
        type=getattr(exctype, '__qualname__', exctype.__name__),
        message=str(exc),
        module=exctype.__module__,
        traceback=format_exception_as_python_does(exc)
    )

