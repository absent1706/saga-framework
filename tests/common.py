from unittest.mock import MagicMock

import typing


class FakeCeleryApp:
    send_task = MagicMock()

    _tasks_handlers: typing.Dict[str, callable]

    def __init__(self):
        self._tasks_handlers = {}

    def task(self, name: str, bind: bool = True,
             *decorator_args, **decorator_kwargs) -> callable:
        def wrapper(task_handler: callable):
            self._tasks_handlers[name] = FakeCeleryTask(self, name, task_handler, bind)

        return wrapper

    def emulate_celery_task_launch(self, name: str, *task_args, **task_kwargs):
        if self._tasks_handlers.get(name) is None:
            raise KeyError(f'Celery task named "{name}" is not registered')

        self._tasks_handlers[name](*task_args, **task_kwargs)


class FakeCeleryTask:
    def __init__(self, celery_app: FakeCeleryApp, name: str, task_handler: callable, bind: bool = False):
        self.app = celery_app
        self.name = name
        self.bind = bind
        self.task_handler = task_handler

    def __call__(self, *args, **kwargs):
        task_handler = self.task_handler

        if self.bind:
            task_handler(self, *args, **kwargs)
        else:
            task_handler(*args, **kwargs)
