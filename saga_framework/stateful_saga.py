__all__ = ['AbstractSagaStateRepository', 'StatefulSaga']

import abc

from celery import Celery

from .base_saga import BaseSaga, BaseStep
from .async_saga import AsyncSaga, AsyncStep


class AbstractSagaStateRepository(abc.ABC):
    @abc.abstractmethod
    def get_saga_state_by_id(self, saga_id: int) -> object:
        raise NotImplementedError

    @abc.abstractmethod
    def update_status(self, saga_id: int, status: str) -> object:
        raise NotImplementedError

    @abc.abstractmethod
    def update(self, saga_id: int, **fields_to_update: str) -> object:
        raise NotImplementedError

    @abc.abstractmethod
    def on_step_failure(self, saga_id: int, failed_step: BaseStep, initial_failure_payload: dict) -> object:
        pass


class StatefulSaga(AsyncSaga, abc.ABC):
    """
    Note this class assumes sqlalchemy-mixins library is used.
    Use it rather as an example
    """
    saga_state_repository: AbstractSagaStateRepository = None
    _saga_state = None  # cached SQLAlchemy instance

    def __init__(self, celery_app: Celery, saga_id: int):
        if not self.saga_state_repository:
            raise AttributeError('to run stateful saga, you must set '
                                 '"saga_state_repository" class property')

        super().__init__(celery_app, saga_id)

    @property
    def saga_state(self):
        if not self._saga_state:
            self._saga_state = self.saga_state_repository.get_saga_state_by_id(self.saga_id)

        return self._saga_state

    def run_step(self, step: BaseStep):
        self.saga_state_repository.update_status(self.saga_id, status=f'{step.name}.running')
        super().run_step(step)

    def compensate_step(self, step: BaseStep, initial_failure_payload: dict):
        self.saga_state_repository.update_status(self.saga_id, status=f'{step.name}.compensating')
        super().compensate_step(step, initial_failure_payload)
        self.saga_state_repository.update_status(self.saga_id, status=f'{step.name}.compensated')

    def on_step_success(self, step: AsyncStep, *args, **kwargs):
        self.saga_state_repository.update_status(self.saga_id, status=f'{step.name}.succeeded')
        super().on_step_success(step, *args, **kwargs)

    def on_step_failure(self, failed_step: AsyncStep, payload: dict):
        self.saga_state_repository.update_status(self.saga_id, status=f'{failed_step.name}.failed')
        super().on_step_failure(failed_step, payload)

    def on_saga_success(self):
        super().on_saga_success()
        self.saga_state_repository.update_status(self.saga_id, 'succeeded')

    def on_saga_failure(self, *args, **kwargs):
        super().on_saga_failure(*args, **kwargs)
        self.saga_state_repository.update_status(self.saga_id, 'failed')

    def compensate(self, failed_step: BaseStep,
                   initial_failure_payload: dict = None):
        self.saga_state_repository.on_step_failure(self.saga_id, failed_step, initial_failure_payload)
        super().compensate(failed_step, initial_failure_payload)

