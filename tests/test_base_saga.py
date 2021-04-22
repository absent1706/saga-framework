from unittest.mock import MagicMock, patch

from saga_framework.base_saga import BaseSaga, SyncStep


def test_saga_run_success():
    step_1_compensation_mock = MagicMock()

    step_2_action_mock = MagicMock()

    on_saga_success_mock = MagicMock()
    on_saga_failure_mock = MagicMock()

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

        on_saga_success = on_saga_success_mock
        on_saga_failure = on_saga_failure_mock

    ###### preparation ended #####

    fake_saga_id = 123
    Saga(fake_saga_id).execute()

    step_2_action_mock.assert_called_once()
    on_saga_success_mock.assert_called_once()

    step_1_compensation_mock.assert_not_called()
    on_saga_failure_mock.assert_not_called()


def test_saga_action_fails():
    step_1_compensation_mock = MagicMock()

    step_2_action_mock = MagicMock()
    step_2_compensation_mock = MagicMock()

    failing_action_mock = MagicMock(
        side_effect=KeyError('some error that may happend in step action'))

    on_saga_success_mock = MagicMock()
    on_saga_failure_mock = MagicMock()

    class Saga(BaseSaga):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

            self.steps = [
                SyncStep(
                    name='step_1',
                    compensation=step_1_compensation_mock
                ),
                SyncStep(
                    name='step_that_fails',
                    action=failing_action_mock
                ),
                SyncStep(
                    name='step_2',
                    action=step_2_action_mock,
                    compensation=step_2_compensation_mock
                )
            ]

        on_saga_success = on_saga_success_mock
        on_saga_failure = on_saga_failure_mock

    ###### preparation ended #####
    fake_saga_id = 123
    Saga(fake_saga_id).execute()

    step_1_compensation_mock.assert_called_once()
    on_saga_failure_mock.assert_called_once()

    step_2_action_mock.assert_not_called()
    step_2_compensation_mock.assert_not_called()
    on_saga_success_mock.assert_not_called()
