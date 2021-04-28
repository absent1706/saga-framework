import typing

import asyncapi

from . import success_task_name, failure_task_name, SagaErrorPayload

fake_asyncapi_servers = {'development': asyncapi.Server(
    url='localhost',
    protocol=asyncapi.ProtocolType.REDIS,
    description="Don't look at this server description, it's just some fake needed to generate AsyncAPI docs"
)}


def message_to_channel(message: asyncapi.Message, response: asyncapi.Message = None, publish_made_first=False, description: str = None) -> typing.Tuple[str, asyncapi.Channel]:
    if publish_made_first:
        first_action, second_action = 'publish', 'subscribe'
    else:
        first_action, second_action = 'subscribe', 'publish'

    channel_kwargs = {
        'description': description,
        first_action: asyncapi.Operation(
            message=message,
        )
    }
    if response:
        channel_kwargs[second_action] = asyncapi.Operation(
            message=response,
        )

    return message.name, asyncapi.Channel(**channel_kwargs)


def message_to_component(message: asyncapi.Message) -> typing.Tuple[str, asyncapi.Message]:
    return message.name, message


def asyncapi_components_from_asyncapi_channels(channels: typing.Iterable[asyncapi.Channel]):
    """
    Allows to more easy generate AsyncApi docs (components sections)

    :param channels:
    :return:
    """

    messages = list()
    for channel in channels:
        if channel.publish and channel.publish.message:
            messages.append(channel.publish.message)
        if channel.subscribe and channel.subscribe.message:
            messages.append(channel.subscribe.message)

    components = [message_to_component(message) for message in messages]
    return asyncapi.Components(messages=dict(components))

#############


def asyncapi_message_for_success_response(base_task_name: str,
                                          title: str = None,
                                          summary: str = None,
                                          payload_dataclass: object = None):
    return asyncapi.Message(
        name=success_task_name(base_task_name),
        title=title,
        summary=summary,
        payload=payload_dataclass
    )


def asyncapi_message_for_failure_response(base_task_name: str,
                                          title: str = None,
                                          summary: str = None,
                                          payload_dataclass: type = SagaErrorPayload):
    return asyncapi.Message(
        name=failure_task_name(base_task_name),
        title=title,
        summary=summary,
        payload=payload_dataclass
    )
