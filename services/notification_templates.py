"""
Notification templates for email, Slack, and webhook notifications.
"""

import logging
from typing import Dict, Any, Optional
from string import Template
from models.notification import NotificationEvent, NotificationChannel

logger = logging.getLogger(__name__)


class NotificationTemplateEngine:
    """
    Template engine for generating notification content with variable substitution.
    """
    
    def __init__(self):
        """Initialize template engine with default templates."""
        self.email_templates = self._initialize_email_templates()
        self.slack_templates = self._initialize_slack_templates()
        self.webhook_templates = self._initialize_webhook_templates()
    
    def _initialize_email_templates(self) -> Dict[NotificationEvent, Dict[str, str]]:
        """
        Initialize email templates for each event type.
        
        Returns:
            Dictionary mapping events to email templates (subject and body)
        """
        return {
            NotificationEvent.SCAN_STARTED: {
                'subject': 'Scan Started: ${domain}',
                'body': '''Hello,

A new scan has been started for ${domain}.

Scan ID: ${scan_id}
Scan Mode: ${scan_mode}
Started At: ${timestamp}

You will receive another notification when the scan completes.

Best regards,
Dynamic Cookie Scanning Service
''',
                'html_body': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c3e50;">Scan Started</h2>
    <p>A new scan has been started for <strong>${domain}</strong>.</p>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Scan ID:</td>
            <td style="padding: 8px;">${scan_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Scan Mode:</td>
            <td style="padding: 8px;">${scan_mode}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Started At:</td>
            <td style="padding: 8px;">${timestamp}</td>
        </tr>
    </table>
    <p>You will receive another notification when the scan completes.</p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #7f8c8d; font-size: 12px;">Dynamic Cookie Scanning Service</p>
</body>
</html>
'''
            },
            NotificationEvent.SCAN_COMPLETED: {
                'subject': 'Scan Completed: ${domain}',
                'body': '''Hello,

The scan for ${domain} has completed successfully.

Scan ID: ${scan_id}
Duration: ${duration} seconds
Total Cookies Found: ${total_cookies}
Pages Scanned: ${pages_scanned}
Completed At: ${timestamp}

View the full results in your dashboard.

Best regards,
Dynamic Cookie Scanning Service
''',
                'html_body': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #27ae60;">✓ Scan Completed</h2>
    <p>The scan for <strong>${domain}</strong> has completed successfully.</p>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Scan ID:</td>
            <td style="padding: 8px;">${scan_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Duration:</td>
            <td style="padding: 8px;">${duration} seconds</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Total Cookies:</td>
            <td style="padding: 8px;">${total_cookies}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Pages Scanned:</td>
            <td style="padding: 8px;">${pages_scanned}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Completed At:</td>
            <td style="padding: 8px;">${timestamp}</td>
        </tr>
    </table>
    <p><a href="${dashboard_url}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Results</a></p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #7f8c8d; font-size: 12px;">Dynamic Cookie Scanning Service</p>
</body>
</html>
'''
            },
            NotificationEvent.SCAN_FAILED: {
                'subject': 'Scan Failed: ${domain}',
                'body': '''Hello,

The scan for ${domain} has failed.

Scan ID: ${scan_id}
Error: ${error}
Failed At: ${timestamp}

Please check the error details and try again.

Best regards,
Dynamic Cookie Scanning Service
''',
                'html_body': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #e74c3c;">✗ Scan Failed</h2>
    <p>The scan for <strong>${domain}</strong> has failed.</p>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Scan ID:</td>
            <td style="padding: 8px;">${scan_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Error:</td>
            <td style="padding: 8px; color: #e74c3c;">${error}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Failed At:</td>
            <td style="padding: 8px;">${timestamp}</td>
        </tr>
    </table>
    <p>Please check the error details and try again.</p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #7f8c8d; font-size: 12px;">Dynamic Cookie Scanning Service</p>
</body>
</html>
'''
            },
            NotificationEvent.COMPLIANCE_VIOLATION: {
                'subject': 'Compliance Violation Detected: ${domain}',
                'body': '''Hello,

A compliance violation has been detected for ${domain}.

Scan ID: ${scan_id}
Violation Type: ${violation_type}
Severity: ${severity}
Details: ${details}
Detected At: ${timestamp}

Please review and take appropriate action.

Best regards,
Dynamic Cookie Scanning Service
''',
                'html_body': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #e67e22;">⚠ Compliance Violation Detected</h2>
    <p>A compliance violation has been detected for <strong>${domain}</strong>.</p>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Scan ID:</td>
            <td style="padding: 8px;">${scan_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Violation Type:</td>
            <td style="padding: 8px;">${violation_type}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Severity:</td>
            <td style="padding: 8px; color: #e67e22;">${severity}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Details:</td>
            <td style="padding: 8px;">${details}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Detected At:</td>
            <td style="padding: 8px;">${timestamp}</td>
        </tr>
    </table>
    <p>Please review and take appropriate action.</p>
    <p><a href="${dashboard_url}" style="background-color: #e67e22; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Details</a></p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #7f8c8d; font-size: 12px;">Dynamic Cookie Scanning Service</p>
</body>
</html>
'''
            },
            NotificationEvent.ANOMALY_DETECTED: {
                'subject': 'Anomaly Detected: ${domain}',
                'body': '''Hello,

An anomaly has been detected in the scan results for ${domain}.

Scan ID: ${scan_id}
Anomaly Type: ${anomaly_type}
Change: ${change}
Details: ${details}
Detected At: ${timestamp}

This may indicate a significant change in cookie behavior.

Best regards,
Dynamic Cookie Scanning Service
''',
                'html_body': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #9b59b6;">⚡ Anomaly Detected</h2>
    <p>An anomaly has been detected in the scan results for <strong>${domain}</strong>.</p>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Scan ID:</td>
            <td style="padding: 8px;">${scan_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Anomaly Type:</td>
            <td style="padding: 8px;">${anomaly_type}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Change:</td>
            <td style="padding: 8px; color: #9b59b6;">${change}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Details:</td>
            <td style="padding: 8px;">${details}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Detected At:</td>
            <td style="padding: 8px;">${timestamp}</td>
        </tr>
    </table>
    <p>This may indicate a significant change in cookie behavior.</p>
    <p><a href="${dashboard_url}" style="background-color: #9b59b6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">View Details</a></p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #7f8c8d; font-size: 12px;">Dynamic Cookie Scanning Service</p>
</body>
</html>
'''
            },
            NotificationEvent.SCHEDULE_CREATED: {
                'subject': 'Schedule Created: ${domain}',
                'body': '''Hello,

A new scan schedule has been created for ${domain}.

Schedule ID: ${schedule_id}
Frequency: ${frequency}
Next Run: ${next_run}
Created At: ${timestamp}

Best regards,
Dynamic Cookie Scanning Service
''',
                'html_body': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #3498db;">Schedule Created</h2>
    <p>A new scan schedule has been created for <strong>${domain}</strong>.</p>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Schedule ID:</td>
            <td style="padding: 8px;">${schedule_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Frequency:</td>
            <td style="padding: 8px;">${frequency}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Next Run:</td>
            <td style="padding: 8px;">${next_run}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Created At:</td>
            <td style="padding: 8px;">${timestamp}</td>
        </tr>
    </table>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #7f8c8d; font-size: 12px;">Dynamic Cookie Scanning Service</p>
</body>
</html>
'''
            },
            NotificationEvent.SCHEDULE_UPDATED: {
                'subject': 'Schedule Updated: ${domain}',
                'body': '''Hello,

The scan schedule for ${domain} has been updated.

Schedule ID: ${schedule_id}
New Frequency: ${frequency}
Next Run: ${next_run}
Updated At: ${timestamp}

Best regards,
Dynamic Cookie Scanning Service
''',
                'html_body': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #3498db;">Schedule Updated</h2>
    <p>The scan schedule for <strong>${domain}</strong> has been updated.</p>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Schedule ID:</td>
            <td style="padding: 8px;">${schedule_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">New Frequency:</td>
            <td style="padding: 8px;">${frequency}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Next Run:</td>
            <td style="padding: 8px;">${next_run}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Updated At:</td>
            <td style="padding: 8px;">${timestamp}</td>
        </tr>
    </table>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #7f8c8d; font-size: 12px;">Dynamic Cookie Scanning Service</p>
</body>
</html>
'''
            },
            NotificationEvent.SCHEDULE_FAILED: {
                'subject': 'Schedule Execution Failed: ${domain}',
                'body': '''Hello,

The scheduled scan for ${domain} has failed to execute.

Schedule ID: ${schedule_id}
Error: ${error}
Failed At: ${timestamp}

Please check the schedule configuration and try again.

Best regards,
Dynamic Cookie Scanning Service
''',
                'html_body': '''
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #e74c3c;">✗ Schedule Execution Failed</h2>
    <p>The scheduled scan for <strong>${domain}</strong> has failed to execute.</p>
    <table style="border-collapse: collapse; margin: 20px 0;">
        <tr>
            <td style="padding: 8px; font-weight: bold;">Schedule ID:</td>
            <td style="padding: 8px;">${schedule_id}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Error:</td>
            <td style="padding: 8px; color: #e74c3c;">${error}</td>
        </tr>
        <tr>
            <td style="padding: 8px; font-weight: bold;">Failed At:</td>
            <td style="padding: 8px;">${timestamp}</td>
        </tr>
    </table>
    <p>Please check the schedule configuration and try again.</p>
    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
    <p style="color: #7f8c8d; font-size: 12px;">Dynamic Cookie Scanning Service</p>
</body>
</html>
'''
            }
        }
    
    def _initialize_slack_templates(self) -> Dict[NotificationEvent, Dict[str, Any]]:
        """
        Initialize Slack message templates for each event type.
        
        Returns:
            Dictionary mapping events to Slack message templates
        """
        return {
            NotificationEvent.SCAN_STARTED: {
                'text': '🚀 Scan started for ${domain}',
                'color': '#3498db',
                'fields': {
                    'Scan ID': '${scan_id}',
                    'Scan Mode': '${scan_mode}',
                    'Started At': '${timestamp}'
                }
            },
            NotificationEvent.SCAN_COMPLETED: {
                'text': '✅ Scan completed for ${domain}',
                'color': 'good',
                'fields': {
                    'Scan ID': '${scan_id}',
                    'Duration': '${duration}s',
                    'Total Cookies': '${total_cookies}',
                    'Pages Scanned': '${pages_scanned}'
                }
            },
            NotificationEvent.SCAN_FAILED: {
                'text': '❌ Scan failed for ${domain}',
                'color': 'danger',
                'fields': {
                    'Scan ID': '${scan_id}',
                    'Error': '${error}',
                    'Failed At': '${timestamp}'
                }
            },
            NotificationEvent.COMPLIANCE_VIOLATION: {
                'text': '⚠️ Compliance violation detected for ${domain}',
                'color': 'warning',
                'fields': {
                    'Scan ID': '${scan_id}',
                    'Violation Type': '${violation_type}',
                    'Severity': '${severity}',
                    'Details': '${details}'
                }
            },
            NotificationEvent.ANOMALY_DETECTED: {
                'text': '⚡ Anomaly detected for ${domain}',
                'color': '#9b59b6',
                'fields': {
                    'Scan ID': '${scan_id}',
                    'Anomaly Type': '${anomaly_type}',
                    'Change': '${change}',
                    'Details': '${details}'
                }
            },
            NotificationEvent.SCHEDULE_CREATED: {
                'text': '📅 Schedule created for ${domain}',
                'color': '#3498db',
                'fields': {
                    'Schedule ID': '${schedule_id}',
                    'Frequency': '${frequency}',
                    'Next Run': '${next_run}'
                }
            },
            NotificationEvent.SCHEDULE_UPDATED: {
                'text': '📅 Schedule updated for ${domain}',
                'color': '#3498db',
                'fields': {
                    'Schedule ID': '${schedule_id}',
                    'New Frequency': '${frequency}',
                    'Next Run': '${next_run}'
                }
            },
            NotificationEvent.SCHEDULE_FAILED: {
                'text': '❌ Schedule execution failed for ${domain}',
                'color': 'danger',
                'fields': {
                    'Schedule ID': '${schedule_id}',
                    'Error': '${error}',
                    'Failed At': '${timestamp}'
                }
            }
        }
    
    def _initialize_webhook_templates(self) -> Dict[NotificationEvent, Dict[str, Any]]:
        """
        Initialize webhook payload templates for each event type.
        
        Returns:
            Dictionary mapping events to webhook payload templates
        """
        # Webhook templates use a generic structure
        return {
            event: {
                'event': event.value,
                'data': {}  # Will be filled with actual data
            }
            for event in NotificationEvent
        }
    
    def render_email(
        self,
        event: NotificationEvent,
        variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Render email template with variable substitution.
        
        Args:
            event: Event type
            variables: Variables to substitute
            
        Returns:
            Dictionary with 'subject', 'body', and 'html_body' keys
        """
        template = self.email_templates.get(event)
        if not template:
            logger.warning(f"No email template found for event {event}")
            return {
                'subject': f"Notification: {event.value}",
                'body': str(variables),
                'html_body': None
            }
        
        try:
            # Substitute variables in templates
            subject = Template(template['subject']).safe_substitute(variables)
            body = Template(template['body']).safe_substitute(variables)
            html_body = Template(template.get('html_body', '')).safe_substitute(variables)
            
            return {
                'subject': subject,
                'body': body,
                'html_body': html_body if html_body else None
            }
        except Exception as e:
            logger.error(f"Error rendering email template for {event}: {e}")
            return {
                'subject': f"Notification: {event.value}",
                'body': str(variables),
                'html_body': None
            }
    
    def render_slack(
        self,
        event: NotificationEvent,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Render Slack message template with variable substitution.
        
        Args:
            event: Event type
            variables: Variables to substitute
            
        Returns:
            Slack message payload dictionary
        """
        template = self.slack_templates.get(event)
        if not template:
            logger.warning(f"No Slack template found for event {event}")
            return {
                'text': f"Notification: {event.value}",
                'fields': variables
            }
        
        try:
            # Substitute variables in text
            text = Template(template['text']).safe_substitute(variables)
            
            # Substitute variables in fields
            fields = {}
            for key, value_template in template.get('fields', {}).items():
                fields[key] = Template(value_template).safe_substitute(variables)
            
            return {
                'text': text,
                'color': template.get('color'),
                'fields': fields
            }
        except Exception as e:
            logger.error(f"Error rendering Slack template for {event}: {e}")
            return {
                'text': f"Notification: {event.value}",
                'fields': variables
            }
    
    def render_webhook(
        self,
        event: NotificationEvent,
        variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Render webhook payload with event data.
        
        Args:
            event: Event type
            variables: Event data
            
        Returns:
            Webhook payload dictionary
        """
        return {
            'event': event.value,
            'data': variables
        }


# Global template engine instance
_template_engine: Optional[NotificationTemplateEngine] = None


def get_template_engine() -> NotificationTemplateEngine:
    """Get the global template engine instance."""
    global _template_engine
    if _template_engine is None:
        _template_engine = NotificationTemplateEngine()
    return _template_engine
