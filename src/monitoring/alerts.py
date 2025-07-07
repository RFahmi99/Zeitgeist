#!/usr/bin/env python3
"""Real-time error alerting and notification system."""

import json
import logging
import smtplib
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Represents a system alert."""
    id: str
    level: str  # critical, warning, info
    component: str
    message: str
    timestamp: datetime
    details: Dict
    resolved: bool = False


@dataclass
class EmailConfig:
    """Email notification configuration."""
    enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    use_tls: bool = True
    from_address: str = ""
    to_address: str = ""
    username: str = ""
    password: str = ""


@dataclass
class WebhookConfig:
    """Webhook notification configuration."""
    enabled: bool = False
    url: str = ""


@dataclass
class AlertConfig:
    """Alert system configuration."""
    email: EmailConfig
    webhook: WebhookConfig


class AlertManager:
    """Manages alert generation and notification delivery."""
    
    def __init__(self, config: AlertConfig):
        self.config = config
        self.alerts = []
        self.alert_history = defaultdict(list)
        self.rate_limits = defaultdict(lambda: {'count': 0, 'window_start': time.time()})
        self.notification_methods = self._setup_notification_methods()
    
    def _setup_notification_methods(self) -> list:
        """Configure available notification methods."""
        methods = []
        
        # Email notifications
        if self.config.email.enabled:
            methods.append(self._send_email_alert)
        
        # Webhook notifications
        if self.config.webhook.enabled:
            methods.append(self._send_webhook_alert)
        
        # File-based alerts (fallback)
        methods.append(self._write_alert_file)
        
        return methods
    
    def send_alert(
        self, 
        level: str, 
        component: str, 
        message: str, 
        details: Optional[Dict] = None
    ):
        """Create and send an alert through configured channels."""
        # Apply rate limiting
        rate_key = f"{component}:{message}"
        if self._is_rate_limited(rate_key):
            logger.debug(f"Alert rate-limited: {rate_key}")
            return
        
        # Create alert instance
        alert = Alert(
            id=f"{component}_{int(time.time())}",
            level=level,
            component=component,
            message=message,
            timestamp=datetime.now(),
            details=details or {}
        )
        
        self.alerts.append(alert)
        self.alert_history[component].append(alert)
        
        # Send notifications for critical/warning alerts
        if level in ['critical', 'warning']:
            self._notify_alert(alert)
        
        logger.error(
            f"Alert {level.upper()}: [{component}] {message}", 
            extra={'alert_details': details}
        )
    
    def _is_rate_limited(
        self, 
        rate_key: str, 
        max_alerts: int = 5, 
        window_minutes: int = 15
    ) -> bool:
        """Check if alerts are rate-limited for a specific key."""
        now = time.time()
        rate_info = self.rate_limits[rate_key]
        
        # Reset window if expired
        if now - rate_info['window_start'] > (window_minutes * 60):
            rate_info['count'] = 0
            rate_info['window_start'] = now
        
        # Enforce rate limit
        if rate_info['count'] >= max_alerts:
            return True
        
        rate_info['count'] += 1
        return False
    
    def _notify_alert(self, alert: Alert):
        """Send notifications through all configured methods."""
        for method in self.notification_methods:
            try:
                method(alert)
            except Exception as error:
                logger.error(
                    f"Failed to send alert via {method.__name__}: {error}"
                )
    
    def _send_email_alert(self, alert: Alert):
        """Send email notification for an alert."""
        if not self.config.email.enabled:
            return
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.email.from_address
            msg['To'] = self.config.email.to_address
            msg['Subject'] = f"[{alert.level.upper()}] Alert: {alert.component}"
            
            body = f"""
Alert Level: {alert.level.upper()}
Component: {alert.component}
Message: {alert.message}
Time: {alert.timestamp.isoformat()}

Details:
{json.dumps(alert.details, indent=2)}

---
Autonomous Blog System
            """.strip()
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(
                self.config.email.smtp_server, 
                self.config.email.smtp_port
            )
            
            if self.config.email.use_tls:
                server.starttls()
                
            if self.config.email.username:
                server.login(
                    self.config.email.username, 
                    self.config.email.password
                )
            
            server.send_message(msg)
            server.quit()
            logger.info(f"Email alert sent: {alert.id}")
            
        except Exception as error:
            logger.error(f"Email alert failed: {error}")
    
    def _send_webhook_alert(self, alert: Alert):
        """Send webhook notification (Discord, Slack, etc.)."""
        if not self.config.webhook.enabled:
            return
            
        try:
            payload = {
                "username": "Blog System Monitor",
                "embeds": [{
                    "title": f"{alert.component} Alert",
                    "description": alert.message,
                    "color": self._get_alert_color(alert.level),
                    "timestamp": alert.timestamp.isoformat(),
                    "fields": [
                        {"name": "Level", "value": alert.level.upper(), "inline": True},
                        {"name": "Component", "value": alert.component, "inline": True},
                        {"name": "Time", "value": alert.timestamp.strftime("%H:%M:%S"), "inline": True}
                    ]
                }]
            }
            
            # Add details if available
            if alert.details:
                details_text = "\n".join(
                    f"**{k}**: {v}" for k, v in alert.details.items()
                )
                payload["embeds"][0]["fields"].append({
                    "name": "Details",
                    "value": details_text[:1000],  # Truncate for limits
                    "inline": False
                })
            
            response = requests.post(
                self.config.webhook.url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Webhook alert sent: {alert.id}")
            
        except Exception as error:
            logger.error(f"Webhook alert failed: {error}")
    
    def _get_alert_color(self, level: str) -> int:
        """Get color code for alert level."""
        return {
            'critical': 0xFF0000,  # Red
            'warning': 0xFFA500,   # Orange
            'info': 0x0080FF       # Blue
        }.get(level, 0x808080)     # Gray default
    
    def _write_alert_file(self, alert: Alert):
        """Write alert to file (fallback method)."""
        try:
            alert_data = {
                'id': alert.id,
                'level': alert.level,
                'component': alert.component,
                'message': alert.message,
                'timestamp': alert.timestamp.isoformat(),
                'details': alert.details
            }
            
            filename = f"alerts_{datetime.now().strftime('%Y%m%d')}.json"
            alerts = self._read_existing_alerts(filename)
            
            alerts.append(alert_data)
            
            with open(filename, 'w') as file:
                json.dump(alerts, file, indent=2)
            
            logger.info(f"Alert written to file: {filename}")
            
        except Exception as error:
            logger.error(f"Failed to write alert file: {error}")
    
    def _read_existing_alerts(self, filename: str) -> List[Dict]:
        """Read existing alerts from file."""
        try:
            with open(filename, 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            logger.warning(f"Corrupted alert file: {filename}")
            return []
    
    def get_active_alerts(self, hours: int = 24) -> List[Alert]:
        """Get unresolved alerts from the last N hours."""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            alert for alert in self.alerts 
            if alert.timestamp >= cutoff and not alert.resolved
        ]
    
    def resolve_alert(self, alert_id: str):
        """Mark an alert as resolved."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.resolved = True
                logger.info(f"Resolved alert: {alert_id}")
                return


# Global alert manager instance
alert_manager: Optional[AlertManager] = None


def initialize_alerts(config: AlertConfig):
    """Initialize the global alert manager."""
    global alert_manager
    alert_manager = AlertManager(config)
    logger.info("Alert system initialized")


def send_critical_alert(component: str, message: str, details: Optional[Dict] = None):
    """Send critical alert."""
    if alert_manager:
        alert_manager.send_alert('critical', component, message, details)


def send_warning_alert(component: str, message: str, details: Optional[Dict] = None):
    """Send warning alert."""
    if alert_manager:
        alert_manager.send_alert('warning', component, message, details)


def send_info_alert(component: str, message: str, details: Optional[Dict] = None):
    """Send informational alert."""
    if alert_manager:
        alert_manager.send_alert('info', component, message, details)