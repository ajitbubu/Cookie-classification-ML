"""
Notification channel implementations for multi-channel notification delivery.
"""

import smtplib
import logging
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import aiohttp
import asyncio
from src.models.notification import Notification, NotificationChannel as ChannelEnum
from src.core.config import NotificationConfig
from src.api.auth.encryption import get_encryption_manager

logger = logging.getLogger(__name__)


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""
    
    @abstractmethod
    async def send(self, notification: Notification, recipient_config: Dict[str, Any]) -> bool:
        """
        Send notification through this channel.
        
        Args:
            notification: Notification to send
            recipient_config: Channel-specific recipient configuration
            
        Returns:
            True if sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_channel_type(self) -> ChannelEnum:
        """Get the channel type enum value."""
        pass


class EmailChannel(NotificationChannel):
    """Email notification channel using SMTP."""
    
    def __init__(self, config: NotificationConfig):
        """
        Initialize email channel.
        
        Args:
            config: Notification configuration with SMTP settings
        """
        self.config = config
        self.smtp_host = config.smtp_host
        self.smtp_port = config.smtp_port
        self.smtp_user = config.smtp_user
        self.smtp_password = config.smtp_password
        self.smtp_from_email = config.smtp_from_email or config.smtp_user
        self.smtp_use_tls = config.smtp_use_tls
        
        if not self.smtp_host:
            logger.warning("SMTP host not configured, email notifications will fail")
    
    def get_channel_type(self) -> ChannelEnum:
        """Get the channel type."""
        return ChannelEnum.EMAIL
    
    async def send(self, notification: Notification, recipient_config: Dict[str, Any]) -> bool:
        """
        Send email notification.
        
        Args:
            notification: Notification to send
            recipient_config: Must contain 'email_address' key
            
        Returns:
            True if sent successfully, False otherwise
        """
        email_address = recipient_config.get('email_address')
        if not email_address:
            logger.error("Email address not provided in recipient config")
            return False
        
        if not self.smtp_host:
            logger.error("SMTP host not configured")
            return False
        
        try:
            # Run SMTP operations in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_email_sync,
                email_address,
                notification
            )
            logger.info(f"Email sent successfully to {email_address} for event {notification.event}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {email_address}: {e}", exc_info=True)
            return False
    
    def _send_email_sync(self, to_address: str, notification: Notification):
        """
        Synchronous email sending (to be run in thread pool).
        
        Args:
            to_address: Recipient email address
            notification: Notification to send
        """
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = notification.data.get('subject', f"Notification: {notification.event}")
        msg['From'] = self.smtp_from_email
        msg['To'] = to_address
        
        # Get body from notification data
        body = notification.data.get('body', '')
        
        # Create plain text and HTML parts
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        # If HTML body is provided, add it
        html_body = notification.data.get('html_body')
        if html_body:
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            if self.smtp_use_tls:
                server.starttls()
            
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            
            server.send_message(msg)


class WebhookChannel(NotificationChannel):
    """Webhook notification channel using HTTP POST."""
    
    def __init__(self, config: NotificationConfig):
        """
        Initialize webhook channel.
        
        Args:
            config: Notification configuration with webhook settings
        """
        self.config = config
        self.timeout = config.webhook_timeout
    
    def get_channel_type(self) -> ChannelEnum:
        """Get the channel type."""
        return ChannelEnum.WEBHOOK
    
    async def send(self, notification: Notification, recipient_config: Dict[str, Any]) -> bool:
        """
        Send webhook notification via HTTP POST.
        
        Args:
            notification: Notification to send
            recipient_config: Must contain 'webhook_url' key (may be encrypted)
            
        Returns:
            True if sent successfully, False otherwise
        """
        webhook_url = recipient_config.get('webhook_url')
        if not webhook_url:
            logger.error("Webhook URL not provided in recipient config")
            return False
        
        # Decrypt webhook URL if it's encrypted
        encryption_manager = get_encryption_manager()
        decrypted_url = encryption_manager.decrypt(webhook_url)
        if decrypted_url:
            webhook_url = decrypted_url
        # If decryption fails, assume URL is not encrypted and use as-is
        
        try:
            # Prepare payload
            payload = {
                'notification_id': str(notification.notification_id) if notification.notification_id else None,
                'event': notification.event,
                'timestamp': notification.created_at.isoformat(),
                'data': notification.data
            }
            
            # Send POST request
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(webhook_url, json=payload) as response:
                    if response.status >= 200 and response.status < 300:
                        logger.info(f"Webhook sent successfully to {webhook_url} for event {notification.event}")
                        return True
                    else:
                        logger.error(
                            f"Webhook failed with status {response.status} for {webhook_url}: "
                            f"{await response.text()}"
                        )
                        return False
                        
        except asyncio.TimeoutError:
            logger.error(f"Webhook timeout after {self.timeout}s for {webhook_url}")
            return False
        except Exception as e:
            logger.error(f"Failed to send webhook to {webhook_url}: {e}", exc_info=True)
            return False


class SlackChannel(NotificationChannel):
    """Slack notification channel using webhook integration."""
    
    def __init__(self, config: NotificationConfig):
        """
        Initialize Slack channel.
        
        Args:
            config: Notification configuration with Slack settings
        """
        self.config = config
        self.timeout = config.webhook_timeout
    
    def get_channel_type(self) -> ChannelEnum:
        """Get the channel type."""
        return ChannelEnum.SLACK
    
    async def send(self, notification: Notification, recipient_config: Dict[str, Any]) -> bool:
        """
        Send Slack notification via webhook.
        
        Args:
            notification: Notification to send
            recipient_config: Must contain 'slack_webhook_url' key (may be encrypted)
            
        Returns:
            True if sent successfully, False otherwise
        """
        slack_webhook_url = recipient_config.get('slack_webhook_url')
        if not slack_webhook_url:
            logger.error("Slack webhook URL not provided in recipient config")
            return False
        
        # Decrypt Slack webhook URL if it's encrypted
        encryption_manager = get_encryption_manager()
        decrypted_url = encryption_manager.decrypt(slack_webhook_url)
        if decrypted_url:
            slack_webhook_url = decrypted_url
        # If decryption fails, assume URL is not encrypted and use as-is
        
        try:
            # Format message for Slack
            slack_message = self._format_slack_message(notification)
            
            # Send POST request to Slack webhook
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(slack_webhook_url, json=slack_message) as response:
                    if response.status == 200:
                        response_text = await response.text()
                        if response_text == 'ok':
                            logger.info(f"Slack notification sent successfully for event {notification.event}")
                            return True
                        else:
                            logger.error(f"Slack webhook returned unexpected response: {response_text}")
                            return False
                    else:
                        logger.error(
                            f"Slack webhook failed with status {response.status}: "
                            f"{await response.text()}"
                        )
                        return False
                        
        except asyncio.TimeoutError:
            logger.error(f"Slack webhook timeout after {self.timeout}s")
            return False
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}", exc_info=True)
            return False
    
    def _format_slack_message(self, notification: Notification) -> Dict[str, Any]:
        """
        Format notification as Slack message.
        
        Args:
            notification: Notification to format
            
        Returns:
            Slack message payload
        """
        # Get text from notification data or create default
        text = notification.data.get('text', f"Notification: {notification.event}")
        
        # Build Slack message with blocks for rich formatting
        message = {
            'text': text,  # Fallback text
        }
        
        # Add blocks if provided in notification data
        blocks = notification.data.get('blocks')
        if blocks:
            message['blocks'] = blocks
        else:
            # Create default block structure
            message['blocks'] = [
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': text
                    }
                }
            ]
            
            # Add fields if provided
            fields = notification.data.get('fields', {})
            if fields:
                field_blocks = []
                for key, value in fields.items():
                    field_blocks.append({
                        'type': 'mrkdwn',
                        'text': f"*{key}:*\n{value}"
                    })
                
                if field_blocks:
                    message['blocks'].append({
                        'type': 'section',
                        'fields': field_blocks
                    })
        
        # Add color/attachment color if provided
        color = notification.data.get('color')
        if color:
            message['attachments'] = [{
                'color': color,
                'blocks': message.get('blocks', [])
            }]
            # Remove blocks from top level if using attachments
            if 'blocks' in message:
                del message['blocks']
        
        return message


class ChannelFactory:
    """Factory for creating notification channel instances."""
    
    @staticmethod
    def create_channel(channel_type: ChannelEnum, config: NotificationConfig) -> NotificationChannel:
        """
        Create a notification channel instance.
        
        Args:
            channel_type: Type of channel to create
            config: Notification configuration
            
        Returns:
            NotificationChannel instance
            
        Raises:
            ValueError: If channel type is not supported
        """
        if channel_type == ChannelEnum.EMAIL:
            return EmailChannel(config)
        elif channel_type == ChannelEnum.WEBHOOK:
            return WebhookChannel(config)
        elif channel_type == ChannelEnum.SLACK:
            return SlackChannel(config)
        else:
            raise ValueError(f"Unsupported channel type: {channel_type}")
    
    @staticmethod
    def create_all_channels(config: NotificationConfig) -> Dict[ChannelEnum, NotificationChannel]:
        """
        Create all available notification channels.
        
        Args:
            config: Notification configuration
            
        Returns:
            Dictionary mapping channel types to channel instances
        """
        return {
            ChannelEnum.EMAIL: EmailChannel(config),
            ChannelEnum.WEBHOOK: WebhookChannel(config),
            ChannelEnum.SLACK: SlackChannel(config)
        }
