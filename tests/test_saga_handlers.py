from dataclasses import asdict

from saga_framework.saga_handlers import saga_step_handler
from saga_framework.utils import serialize_saga_error
from .common import FakeCeleryApp


# noinspection PyPep8Naming
def test_saga_step_handler_success():
    fake_celery_app = FakeCeleryApp()
    SAGA_STEP_NAME = 'step_1'

    RESPONSE_QUEUE_NAME = 'some_fake_queue'
    RESPONSE_PAYLOAD = {'some': 'saga handler response payload'}
    fake_saga_id = 123

    @fake_celery_app.task(bind=True, name=SAGA_STEP_NAME)
    @saga_step_handler(response_queue=RESPONSE_QUEUE_NAME)
    def some_celery_task(self, saga_id: int, payload: dict) -> dict:
        return RESPONSE_PAYLOAD

    fake_celery_app.emulate_celery_task_launch(
        SAGA_STEP_NAME,
        saga_id=fake_saga_id,
        payload={'some': 'saga step payload that orchestrator passed'}
    )

    # make sure that, after Celery task finishes successfully,
    #  @saga_step_handler automnatically sends a response
    #   which is a Celery task that Orchestrator will listen to
    #    and launch next saga step
    fake_celery_app.send_task.assert_called_with(
        f'{SAGA_STEP_NAME}.response.success',
        args=[
            fake_saga_id,
            RESPONSE_PAYLOAD
        ],
        queue=RESPONSE_QUEUE_NAME
    )


# noinspection PyPep8Naming
def test_saga_step_handler_failure():
    fake_celery_app = FakeCeleryApp()
    SAGA_STEP_NAME = 'step_1'

    RESPONSE_QUEUE_NAME = 'some_fake_queue'
    fake_saga_id = 123
    exception_that_step_handler_raises = Exception('some exception in saga step handler')

    @fake_celery_app.task(bind=True, name=SAGA_STEP_NAME)
    @saga_step_handler(response_queue=RESPONSE_QUEUE_NAME)
    def some_celery_task(self, saga_id: int, payload: dict) -> dict:
        raise exception_that_step_handler_raises

    fake_celery_app.emulate_celery_task_launch(
        SAGA_STEP_NAME,
        saga_id=fake_saga_id,
        payload={'some': 'saga step payload that orchestrator passed'}
    )

    # make sure that, after Celery task raises an error,
    #  @saga_step_handler catches it and reports a failure to Orchestrator,
    #   namely, sends a Celery task that Orchestrator will listen to
    #    and rollback a saga
    fake_celery_app.send_task.assert_called_with(
        f'{SAGA_STEP_NAME}.response.failure',
        args=[
            fake_saga_id,
            asdict(serialize_saga_error(exception_that_step_handler_raises))
        ],
        queue=RESPONSE_QUEUE_NAME
    )
