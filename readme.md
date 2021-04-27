Framework implementing Saga pattern ("orchestration" flavour) for microservices

It's a Python alternative of [Eventuate Tram Sagas library](https://eventuate.io/docs/manual/eventuate-tram/latest/getting-started-eventuate-tram-sagas.html)
 that's promoted in [Chris Richardson book on Microservices](https://microservices.io/book)

What's cool there:
 * Saga classes for Saga Orchestrator
 * Saga state keeping (with `StatefulSaga` class)
 * Celery integration
 * AsyncAPI integration  
 * [Practical usage example](https://github.com/absent1706/saga-demo) (`CreateOrder` saga from [Chris Richardson book on Microservices](https://microservices.io/book))

# Implementation notes
There're three Saga classes covering use cases from trivial (`BaseSaga`) to real-world ones (`StatefulSaga`)

## BaseSaga
Simplest class which is an analogue of [saga_py](https://github.com/flowpl/saga_py)

```python
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

###### how to use this class #####
fake_saga_id = 123
Saga(fake_saga_id).execute()

```
As simple as that.
Determine saga steps and run them.

## AsyncSaga
Here's where story begins.

In real world, Saga steps are handled by other microservices which Orchestrator service launches
by means of sending a message to message broker (in case of Python, it will correspond to sending Celery task).

When other service (let's call it Saga Step Handler) receives a message (Celery task), 
 it runs some business logic (e.g., Accounting service will charge a given customer).
After that, it responds back by means of sending another message to a broker (in Python, it means sending another Celery task).

Orchestrator listens to such messages (it has its own Celery worker for that) and:
 * for success responses (here they look like `{base_task_name}.response.success`), launches next saga step
 * for failure responses (here they look like `{base_task_name}.response.failure`), rolls back a saga

This framework has all tools needed to implement such a complex flow:
 * `AsyncSaga` and `AsyncStep` classes - support sending Celery tasks to Saga Step Handler microservices
 * `saga_step_handler` - decorator for Celery task for usage in Saga Step Handler services. Sends `{base_task_name}.response.success` or `{base_task_name}.response.failure` Celery task automatically

In addition, there're some bells and whistles:
 * custom `on_success` and `on_failure` callbacks in `AsyncStep` class which are called when corresponding step succeeds or fails
 * `auto_retry_then_reraise` decorator for Celery task. Has no relation to Sagas per se, but is useful because sometimes it's needed to retry Celery task few times and only then fail

Here's a usage example of `AsyncSaga` and `AsyncStep` (see [a real usage example here](https://github.com/absent1706/saga-demo))
```python
class Saga(AsyncSaga):
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
```


Here's a usage example of Saga Step Handler (using `saga_step_handler` and `auto_retry_then_reraise` decorators).
See more at [a real usage example repo](https://github.com/absent1706/saga-demo)
```python
@command_handlers_celery_app.task(
    bind=True, name=approve_ticket_message.TASK_NAME,
    default_retry_delay=5  # set some small retry delay to not wait 3 minutes Celery sets by default
)
@saga_step_handler(response_queue=CREATE_ORDER_SAGA_RESPONSE_QUEUE)
@auto_retry_then_reraise(max_retries=2)  # retry task 2 times, then re-raise exception
def approve_ticket_task(self: Task, saga_id: int, payload: dict) -> typing.Union[dict, None]:
    request_data = approve_ticket_message.Payload(**payload)

    # emulate 50%-probable first-time failure
    if random.random() < 0.3:
        raise EnvironmentError('test error message. Task will retry now')

    # in real world, we would change ticket status to 'approved' in service DB
    logging.info(f'Restaurant ticket {request_data.ticket_id} approved')

    return None
```

**TODO: order service-> register celry workers**

## StatefulSaga
**TODO**

## AsyncAPI integration
**TODO**

## Real-world example
**TODO: promote my another repo**

# Development
See more at https://packaging.python.org/tutorials/packaging-projects/

## Setup
`pip3 install -r requirements.dev.txt`

## Build
Specify version in `setup.py`, then

```
python3 setup.py sdist bdist_wheel
twine check dist/*
```

## Upload to PyPi
```
twine upload dist/*
```

