from unittest.mock import MagicMock, patch

from celery import Celery

from saga_framework import BaseSaga, SyncStep, AsyncStep


step_1_compensation_mock = MagicMock()
step_2_action_mock = MagicMock()
on_success_mock = MagicMock()


class Saga(BaseSaga):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.steps = [
            SyncStep(
                name='step_1',
                compensation=step_1_compensation_mock
            ),
            SyncStep(
                name='step_2',
                action=step_2_action_mock
            )
        ]


def test_saga_run_success():
    with patch.object(Saga, 'on_saga_success', on_success_mock):
        celery_app = Celery()
        fake_saga_id = 123
        Saga(celery_app, fake_saga_id).execute()

        step_2_action_mock.assert_called_once()
        on_success_mock.assert_called_once()

        step_1_compensation_mock.assert_not_called()

