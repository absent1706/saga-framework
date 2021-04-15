__all__ = ['auto_retry_then_reraise']

import functools

from celery import Task
from celery.exceptions import MaxRetriesExceededError


def auto_retry_then_reraise(max_retries: int = 3, **retry_kwargs):
    """
    Retry max_retries times.
    If all retries failed, reraise initially risen error.

    Apply this decorator after Celery's @task decorator.
    For example:
        @celery_app.task(bind=True)
        @reraise_exception_after_max_retries_exceeded(max_retries=5)

    Note: it's important to set bind=True in @task
      because this decorator will need access to celery task instance
    """
    def inner(func):

        @functools.wraps(func)
        def wrapper(self: Task, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as exc:
                try:
                    raise self.retry(exc=exc, max_retries=max_retries, **retry_kwargs)
                except MaxRetriesExceededError:
                    raise exc

        return wrapper
    return inner
