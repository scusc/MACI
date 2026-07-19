"""
Azure Service Bus client manager for cross-service asynchronous events.
"""
import logging
import json
from typing import Callable, Any
import asyncio

from azure.servicebus.aio import ServiceBusClient, ServiceBusSender, ServiceBusReceiver
from azure.identity.aio import DefaultAzureCredential
from azure.servicebus import ServiceBusMessage

from maci_core.config import settings

logger = logging.getLogger("maci_core.events.bus")

class ServiceBusClientManager:
    """Manages publishing and subscribing to Azure Service Bus Topics."""
    
    def __init__(self, fully_qualified_namespace: str = None):
        # Allow fallback to connection string for local development if needed, 
        # but prefer DefaultAzureCredential (Managed Identity / Azure CLI)
        self.namespace = fully_qualified_namespace or getattr(settings, "SERVICE_BUS_NAMESPACE", None)
        self.connection_string = getattr(settings, "SERVICE_BUS_CONNECTION_STRING", None)
        self.client = None
        self.credential = None
        
    async def connect(self):
        if not self.client:
            if self.namespace:
                logger.info(f"Connecting to Service Bus namespace: {self.namespace}")
                self.credential = DefaultAzureCredential()
                self.client = ServiceBusClient(
                    fully_qualified_namespace=self.namespace,
                    credential=self.credential
                )
            elif self.connection_string:
                logger.info("Connecting to Service Bus via Connection String")
                self.client = ServiceBusClient.from_connection_string(
                    conn_str=self.connection_string
                )
            else:
                logger.warning("No Service Bus configuration found. Async events will be disabled or mocked.")

    async def close(self):
        if self.client:
            await self.client.close()
        if self.credential:
            await self.credential.close()
            
    async def publish_event(self, topic_name: str, event_data: dict):
        """Publishes an event to a Service Bus Topic."""
        if not self.client:
            await self.connect()
            
        if not self.client:
            logger.info(f"[MOCK SERVICE BUS] Published to {topic_name}: {json.dumps(event_data)}")
            return
            
        try:
            sender: ServiceBusSender = self.client.get_topic_sender(topic_name=topic_name)
            async with sender:
                message = ServiceBusMessage(json.dumps(event_data))
                await sender.send_messages(message)
                logger.info(f"Published event to {topic_name}")
        except Exception as e:
            logger.error(f"Failed to publish event to {topic_name}: {e}")
            raise
            
    async def listen_to_subscription(
        self, 
        topic_name: str, 
        subscription_name: str, 
        message_handler: Callable[[dict], Any]
    ):
        """Listens to a Service Bus Subscription indefinitely."""
        if not self.client:
            await self.connect()
            
        if not self.client:
            logger.warning(f"[MOCK SERVICE BUS] Cannot listen to {topic_name}/{subscription_name} without config.")
            return

        logger.info(f"Starting listener for {topic_name}/{subscription_name}")
        receiver: ServiceBusReceiver = self.client.get_subscription_receiver(
            topic_name=topic_name, 
            subscription_name=subscription_name
        )
        
        async with receiver:
            while True:
                try:
                    messages = await receiver.receive_messages(max_message_count=10, max_wait_time=5)
                    for msg in messages:
                        try:
                            # Parse JSON body
                            body = b"".join(msg.body).decode("utf-8")
                            data = json.loads(body)
                            
                            # Handle message
                            if asyncio.iscoroutinefunction(message_handler):
                                await message_handler(data)
                            else:
                                message_handler(data)
                                
                            # Complete message
                            await receiver.complete_message(msg)
                            logger.info(f"Successfully processed message from {subscription_name}")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")
                            await receiver.abandon_message(msg)
                except Exception as e:
                    logger.error(f"Error receiving messages from Service Bus: {e}")
                    await asyncio.sleep(5)  # Backoff

# Global instance for shared use
bus_manager = ServiceBusClientManager()
