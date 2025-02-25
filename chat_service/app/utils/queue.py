import json
import logging
import uuid
from typing import Any, Dict, Optional, Callable, Awaitable
import aio_pika
from aio_pika import Message, DeliveryMode, ExchangeType

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global RabbitMQ connection and channel
rabbitmq_connection: Optional[aio_pika.Connection] = None
rabbitmq_channel: Optional[aio_pika.Channel] = None


async def init_rabbitmq() -> None:
    """Initialize RabbitMQ connection and channel."""
    global rabbitmq_connection, rabbitmq_channel

    try:
        # Connect to RabbitMQ
        rabbitmq_connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)

        # Create channel
        rabbitmq_channel = await rabbitmq_connection.channel()
        await rabbitmq_channel.set_qos(prefetch_count=10)

        # Declare main queue
        main_queue = await rabbitmq_channel.declare_queue(
            settings.RABBITMQ_QUEUE_NAME,
            durable=True,
            arguments={
                "x-dead-letter-exchange": "dlx",
                "x-dead-letter-routing-key": settings.RABBITMQ_DEAD_LETTER_QUEUE,
                "x-message-ttl": 86400000,  # 24 hours
            },
        )

        # Declare dead letter exchange and queue
        dlx = await rabbitmq_channel.declare_exchange("dlx", ExchangeType.DIRECT)

        dead_letter_queue = await rabbitmq_channel.declare_queue(
            settings.RABBITMQ_DEAD_LETTER_QUEUE, durable=True
        )

        await dead_letter_queue.bind(dlx, settings.RABBITMQ_DEAD_LETTER_QUEUE)

        logger.info("RabbitMQ connection established successfully")
    except Exception as e:
        logger.error(f"Error connecting to RabbitMQ: {e}")
        if rabbitmq_connection:
            await rabbitmq_connection.close()
        raise


async def close_rabbitmq() -> None:
    """Close RabbitMQ connection and channel."""
    global rabbitmq_connection, rabbitmq_channel

    if rabbitmq_channel:
        await rabbitmq_channel.close()

    if rabbitmq_connection:
        await rabbitmq_connection.close()

    logger.info("RabbitMQ connection closed")


async def get_rabbitmq_channel() -> aio_pika.Channel:
    """
    Get RabbitMQ channel.

    Returns:
        aio_pika.Channel: RabbitMQ channel

    Raises:
        RuntimeError: If RabbitMQ channel is not initialized
    """
    if not rabbitmq_channel:
        raise RuntimeError("RabbitMQ channel not initialized")
    return rabbitmq_channel


async def publish_message(
    data: Dict[str, Any],
    queue_name: str = settings.RABBITMQ_QUEUE_NAME,
    priority: int = 0,
) -> str:
    """
    Publish message to RabbitMQ queue.

    Args:
        data (Dict[str, Any]): Message data
        queue_name (str, optional): Queue name. Defaults to settings.RABBITMQ_QUEUE_NAME.
        priority (int, optional): Message priority (0-9). Defaults to 0.

    Returns:
        str: Message ID

    Raises:
        RuntimeError: If RabbitMQ channel is not initialized
    """
    channel = await get_rabbitmq_channel()

    # Generate message ID
    message_id = str(uuid.uuid4())

    # Add message ID to data
    if "id" not in data:
        data["id"] = message_id

    # Create message
    message = Message(
        body=json.dumps(data).encode(),
        message_id=message_id,
        delivery_mode=DeliveryMode.PERSISTENT,
        priority=priority,
        headers={"x-retry-count": 0},
    )

    # Publish message
    await channel.default_exchange.publish(message, routing_key=queue_name)

    logger.debug(f"Published message {message_id} to queue {queue_name}")

    return message_id


async def consume_messages(
    callback: Callable[[Dict[str, Any]], Awaitable[None]],
    queue_name: str = settings.RABBITMQ_QUEUE_NAME,
) -> None:
    """
    Consume messages from RabbitMQ queue.

    Args:
        callback (Callable): Async callback function to process messages
        queue_name (str, optional): Queue name. Defaults to settings.RABBITMQ_QUEUE_NAME.

    Example:
        ```
        async def process_message(data: Dict[str, Any]) -> None:
            # Process message
            print(f"Processing message: {data}")

        await consume_messages(process_message)
        ```
    """
    channel = await get_rabbitmq_channel()
    queue = await channel.get_queue(queue_name)

    async def process_message(message: aio_pika.IncomingMessage) -> None:
        """Process incoming message."""
        async with message.process():
            try:
                # Decode message body
                body = message.body.decode()
                data = json.loads(body)

                # Call callback function
                await callback(data)

            except Exception as e:
                # Get retry count from message headers
                headers = message.headers or {}
                retry_count = headers.get("x-retry-count", 0) + 1

                if retry_count <= settings.MAX_RETRIES:
                    # Requeue message with incremented retry count
                    logger.warning(
                        f"Error processing message {message.message_id}: {e}. "
                        f"Retrying ({retry_count}/{settings.MAX_RETRIES})..."
                    )

                    # Create new message with incremented retry count
                    new_message = Message(
                        body=message.body,
                        headers={**headers, "x-retry-count": retry_count},
                        delivery_mode=DeliveryMode.PERSISTENT,
                        message_id=message.message_id,
                    )

                    # Publish new message
                    await channel.default_exchange.publish(
                        new_message, routing_key=queue_name
                    )
                else:
                    # Max retries reached, send to dead letter queue
                    logger.error(
                        f"Max retries reached for message {message.message_id}. "
                        f"Error: {e}"
                    )

                    # Message will be automatically sent to dead letter queue

    # Start consuming messages
    await queue.consume(process_message)
    logger.info(f"Started consuming messages from queue {queue_name}")
