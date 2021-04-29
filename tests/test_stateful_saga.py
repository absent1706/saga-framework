from dataclasses import dataclass
from unittest.mock import MagicMock

import typing

from saga_framework.async_saga import AsyncStep
from saga_framework.base_saga import SyncStep
from saga_framework.stateful_saga import StatefulSaga, \
    AbstractSagaStateRepository
from .common import FakeCeleryApp


@dataclass
class FakeSagaState:
    id: int
    status: typing.Optional[str] = None


class FakeRepository(AbstractSagaStateRepository):
    _saga_states: typing.Dict[int, FakeSagaState] = None

    def get_saga_state_by_id(self, saga_id: int) -> object:
        return self._saga_states[saga_id]

    def update_status(self, saga_id: int, status: str) -> object:
        saga_state = self.get_saga_state_by_id(saga_id)
        saga_state.status = status
        return saga_state

    def update(self, saga_id: int, **fields_to_update: str) -> object:
        raise NotImplementedError

    on_step_failure = MagicMock()


def test_saga_run_success():
    step_1_compensation_mock = MagicMock()

    step_2_action_mock = MagicMock()
    step_2_on_success_mock = MagicMock()
    step_2_on_failure_mock = MagicMock()

    step_3_action_mock = MagicMock()

    class Saga(StatefulSaga):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.steps = [
                SyncStep(
                    name='step_1',
                    compensation=step_1_compensation_mock
                ),
                AsyncStep(
                    name='step_2',
                    action=step_2_action_mock,

                    queue='some_queue',
                    base_task_name='step_2_task',
                    on_success=step_2_on_success_mock,
                    on_failure=step_2_on_failure_mock
                ),
                SyncStep(
                    name='step_3',
                    action=step_3_action_mock
                ),
            ]

    fake_celery_app = FakeCeleryApp()

    ############# Preraration ended. Launching a test #############

    fake_saga_id = 123

    repository = FakeRepository()
    repository._saga_states = {fake_saga_id: FakeSagaState(id=fake_saga_id)}

    # register 'response' Celery tasks handlers.
    # It's crucial part to make Saga Orchestrator
    #  launch next saga step (or rollback saga) when Saga Handler service
    #  returns result (via Celery task)
    # noinspection PyTypeChecker
    Saga.register_async_step_handlers(repository, fake_celery_app)

    # launch saga
    Saga(repository, fake_celery_app, fake_saga_id).execute()

    # check that status is correct (step 2 is running until we have response from Celery)
    assert repository._saga_states[fake_saga_id].status == 'step_2.running'

    # emulate that Step Handler service successfully handled step 2
    #  and triggered corresponding Celery task on Saga Orchestrator
    celery_task_params = dict(
        saga_id=fake_saga_id,
        payload={'ticket_id': '111'}
    )
    fake_celery_app.emulate_celery_task_launch('step_2_task.response.success', **celery_task_params)

    # check that status is correct after saga successfully runs
    assert repository._saga_states[fake_saga_id].status == 'succeeded'


def test_saga_run_failure():
    step_1_compensation_mock = MagicMock()

    step_2_action_mock = MagicMock()
    step_2_on_success_mock = MagicMock()
    step_2_on_failure_mock = MagicMock()

    step_3_action_mock = MagicMock()

    class Saga(StatefulSaga):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.steps = [
                SyncStep(
                    name='step_1',
                    compensation=step_1_compensation_mock
                ),
                AsyncStep(
                    name='step_2',
                    action=step_2_action_mock,

                    queue='some_queue',
                    base_task_name='step_2_task',
                    on_success=step_2_on_success_mock,
                    on_failure=step_2_on_failure_mock
                ),
                SyncStep(
                    name='step_3',
                    action=step_3_action_mock
                )
            ]

    fake_celery_app = FakeCeleryApp()

    ############# Preraration ended. Launching a test #############
    fake_saga_id = 123

    repository = FakeRepository()
    repository._saga_states = {fake_saga_id: FakeSagaState(id=fake_saga_id)}

    # register 'response' Celery tasks handlers.
    # It's crucial part to make Saga Orchestrator
    #  launch next saga step (or rollback saga) when Saga Handler service
    #  returns result (via Celery task)
    # noinspection PyTypeChecker
    Saga.register_async_step_handlers(repository, fake_celery_app)

    # launch saga
    Saga(repository, fake_celery_app, fake_saga_id).execute()

    # check that status is correct (step 2 is running until we have response from Celery)
    assert repository._saga_states[fake_saga_id].status == 'step_2.running'

    # emulate that Step Handler service successfully handled step 2
    #  and triggered corresponding Celery task on Saga Orchestrator
    celery_task_params = dict(
        saga_id=fake_saga_id,
        payload={'ticket_id': '111'}
    )
    fake_celery_app.emulate_celery_task_launch('step_2_task.response.failure', **celery_task_params)

    # check that status is correct after saga fails
    assert repository._saga_states[fake_saga_id].status == 'failed'

