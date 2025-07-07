import os
import logging
from dataclasses import dataclass
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    db_type: str = os.getenv('DB_TYPE', 'postgres')
    db_path: str = "blog_system.db"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    
    @classmethod
    def from_env(cls):
        return cls(
            db_type=os.getenv('DB_TYPE', 'sqlite'),
            db_path=os.getenv('DB_PATH', 'blog_system.db'),
            backup_enabled=os.getenv('DB_BACKUP_ENABLED', 'true').lower() == 'true',
            backup_interval_hours=int(os.getenv('DB_BACKUP_INTERVAL', '24'))
        )


@dataclass
class ScrapingConfig:
    """Web scraping configuration settings"""
    max_retries: int = 3
    timeout: int = 180  # Increased to 3 minutes
    wait_time: int = 5
    max_sources_per_topic: int = 5
    user_agent_rotation: bool = True
    
    @classmethod
    def from_env(cls):
        return cls(
            max_retries=int(os.getenv('SCRAPING_MAX_RETRIES', '3')),
            timeout=int(os.getenv('SCRAPING_TIMEOUT', '30')),
            wait_time=int(os.getenv('SCRAPING_WAIT_TIME', '3')),
            max_sources_per_topic=int(os.getenv('MAX_SOURCES_PER_TOPIC', '5')),
            user_agent_rotation=os.getenv('USER_AGENT_ROTATION', 'true').lower() == 'true'
        )


@dataclass
class AIConfig:
    """AI model configuration settings"""
    model_name: str = "mistral"
    max_tokens: int = 8192
    temperature: float = 0.7
    timeout: int = 900
    max_retries: int = 3
    min_content_length: int = 300
    max_content_length: int = 8000
    
    @classmethod
    def from_env(cls):
        return cls(
            model_name=os.getenv('AI_MODEL', 'mistral'),
            max_tokens=int(os.getenv('AI_MAX_TOKENS', '4000')),
            temperature=float(os.getenv('AI_TEMPERATURE', '0.7')),
            timeout=int(os.getenv('AI_TIMEOUT', '300')),
            max_retries=int(os.getenv('AI_MAX_RETRIES', '3')),
            min_content_length=int(os.getenv('MIN_CONTENT_LENGTH', '500')),
            max_content_length=int(os.getenv('MAX_CONTENT_LENGTH', '8000'))
        )


@dataclass
class SchedulingConfig:
    """Scheduling configuration settings"""
    enabled: bool = True
    interval_hours: int = 6
    max_posts_per_day: int = 8
    business_hours_only: bool = False
    timezone: str = "UTC"
    
    @classmethod
    def from_env(cls):
        return cls(
            enabled=os.getenv('SCHEDULING_ENABLED', 'true').lower() == 'true',
            interval_hours=int(os.getenv('SCHEDULING_INTERVAL', '6')),
            max_posts_per_day=int(os.getenv('MAX_POSTS_PER_DAY', '8')),
            business_hours_only=os.getenv('BUSINESS_HOURS_ONLY', 'false').lower() == 'true',
            timezone=os.getenv('TIMEZONE', 'UTC')
        )


@dataclass
class PublishingConfig:
    """Publishing configuration settings"""
    platforms: List[str] = None
    auto_publish: bool = True
    require_approval: bool = False
    seo_optimization: bool = True
    
    def __post_init__(self):
        if self.platforms is None:
            self.platforms = ["html", "notion"]
    
    @classmethod
    def from_env(cls):
        platforms = os.getenv('PUBLISHING_PLATFORMS', 'html,notion').split(',')
        return cls(
            platforms=[p.strip() for p in platforms],
            auto_publish=os.getenv('AUTO_PUBLISH', 'true').lower() == 'true',
            require_approval=os.getenv('REQUIRE_APPROVAL', 'false').lower() == 'true',
            seo_optimization=os.getenv('SEO_OPTIMIZATION', 'true').lower() == 'true'
        )


@dataclass
class LoggingConfig:
    """Logging configuration settings"""
    level: str = "INFO"
    file: str = "blog_system.log"
    max_size_mb: int = 10
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    json_logging: bool = False
    
    @classmethod
    def from_env(cls):
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            file=os.getenv('LOG_FILE', 'blog_system.log'),
            max_size_mb=int(os.getenv('LOG_MAX_SIZE_MB', '10')),
            backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
            json_logging=os.getenv('JSON_LOGGING', 'false').lower() == 'true'
        )


@dataclass
class EmailConfig:
    """Email notification configuration settings"""
    enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    from_address: str = ""
    to_address: str = ""
    username: str = ""
    password: str = ""

    @classmethod
    def from_env(cls):
        return cls(
            enabled=os.getenv('EMAIL_ENABLED', 'false').lower() == 'true',
            smtp_server=os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
            smtp_port=int(os.getenv('EMAIL_SMTP_PORT', '587')),
            from_address=os.getenv('EMAIL_FROM_ADDRESS', ''),
            to_address=os.getenv('EMAIL_TO_ADDRESS', ''),
            username=os.getenv('EMAIL_USERNAME', ''),
            password=os.getenv('EMAIL_PASSWORD', '')
        )


@dataclass  
class WebhookConfig:
    """Webhook configuration settings"""
    enabled: bool = False
    url: str = ""

    @classmethod
    def from_env(cls):
        return cls(
            enabled=os.getenv('WEBHOOK_ENABLED', 'false').lower() == 'true',
            url=os.getenv('WEBHOOK_URL', '')
        )


@dataclass
class BlogConfig:
    """Main configuration class aggregating all settings"""
    database: DatabaseConfig = None
    scraping: ScrapingConfig = None
    ai: AIConfig = None
    scheduling: SchedulingConfig = None
    publishing: PublishingConfig = None
    logging: LoggingConfig = None
    email: EmailConfig = None
    webhook: WebhookConfig = None
    
    def __post_init__(self):
        self.database = self.database or DatabaseConfig.from_env()
        self.scraping = self.scraping or ScrapingConfig.from_env()
        self.ai = self.ai or AIConfig.from_env()
        self.scheduling = self.scheduling or SchedulingConfig.from_env()
        self.publishing = self.publishing or PublishingConfig.from_env()
        self.logging = self.logging or LoggingConfig.from_env()
        self.email = self.email or EmailConfig.from_env()
        self.webhook = self.webhook or WebhookConfig.from_env()
    
    @classmethod
    def from_env(cls):
        return cls()
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        if not 0.0 <= self.ai.temperature <= 1.0:
            issues.append("AI temperature must be between 0.0 and 1.0")
        
        if self.scraping.timeout < 10:
            issues.append("Scraping timeout too low (minimum 10 seconds)")
            
        if self.scheduling.max_posts_per_day > 20:
            issues.append("Max posts per day too high (max 20 recommended)")

        if self.ai.timeout < 60:
            issues.append("AI timeout too low (minimum 60 seconds)")
        
        if self.scheduling.interval_hours < 1:
            issues.append("Scheduling interval too low (minimum 1 hour)")
        
        if self.scraping.max_sources_per_topic > 10:
            issues.append("Too many sources per topic (max 10 recommended)")
        
        if not self.publishing.platforms:
            issues.append("No publishing platforms configured")
        
        return issues
    
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary"""
        return {
            "ai_model": self.ai.model_name,
            "scheduling_enabled": self.scheduling.enabled,
            "interval_hours": self.scheduling.interval_hours,
            "max_sources": self.scraping.max_sources_per_topic,
            "publishing_platforms": self.publishing.platforms,
            "auto_publish": self.publishing.auto_publish,
            "log_level": self.logging.level
        }


# Global configuration instance
config = BlogConfig.from_env()