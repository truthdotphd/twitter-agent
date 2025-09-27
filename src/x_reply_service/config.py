"""Configuration management for the X.com Auto-Reply Service."""

import os
import yaml
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from .models import Config, APIConfig, SelectionConfig, ReplyConfig, RateLimitConfig, AppConfig


class ConfigManager:
    """Manages application configuration from files and environment variables."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file. If None, uses default locations.
        """
        self.config_path = config_path or self._find_config_file()
        self.config: Optional[Config] = None
        
        # Load environment variables
        load_dotenv()
    
    def _find_config_file(self) -> str:
        """Find configuration file in standard locations."""
        possible_paths = [
            "config/config.yaml",
            "config.yaml",
            os.path.expanduser("~/.x_reply_service/config.yaml"),
            "/etc/x_reply_service/config.yaml"
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # If no config file found, use the example as template
        return "config/config.yaml.example"
    
    def load_config(self) -> Config:
        """Load configuration from file and environment variables."""
        if self.config is not None:
            return self.config
        
        # Load from YAML file
        config_data = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        # Build API config from environment variables
        api_config = APIConfig(
            twitter_bearer_token=os.getenv('TWITTER_BEARER_TOKEN', ''),
            twitter_api_key=os.getenv('TWITTER_API_KEY', ''),
            twitter_api_secret=os.getenv('TWITTER_API_SECRET', ''),
            twitter_access_token=os.getenv('TWITTER_ACCESS_TOKEN', ''),
            twitter_access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET', ''),
            perplexity_api_key=os.getenv('PERPLEXITY_API_KEY', '')
        )
        
        # Build other configs from YAML with defaults
        selection_config = SelectionConfig(**config_data.get('selection', {}))
        reply_config = ReplyConfig(**config_data.get('reply', {}))
        rate_limits_config = RateLimitConfig(**config_data.get('rate_limits', {}))
        app_config = AppConfig(**config_data.get('app', {}))
        
        # Create complete configuration
        self.config = Config(
            api=api_config,
            selection=selection_config,
            reply=reply_config,
            rate_limits=rate_limits_config,
            app=app_config
        )
        
        return self.config
    
    def validate_config(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if not self.config:
            self.load_config()
        
        # Validate API credentials
        api = self.config.api
        required_fields = [
            ('twitter_bearer_token', api.twitter_bearer_token),
            ('twitter_api_key', api.twitter_api_key),
            ('twitter_api_secret', api.twitter_api_secret),
            ('twitter_access_token', api.twitter_access_token),
            ('twitter_access_token_secret', api.twitter_access_token_secret),
            ('perplexity_api_key', api.perplexity_api_key)
        ]
        
        for field_name, field_value in required_fields:
            if not field_value or field_value.strip() == '':
                errors.append(f"Missing required API credential: {field_name}")
        
        # Validate directories exist
        data_dir = Path(self.config.app.data_dir)
        log_dir = Path(self.config.app.log_dir)
        
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create data directory {data_dir}: {e}")
        
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create log directory {log_dir}: {e}")
        
        # Validate selection config
        if self.config.selection.max_tweets_per_run > 20:
            errors.append("max_tweets_per_run should not exceed 20 to avoid rate limits")
        
        if self.config.selection.max_tweet_age_hours > 24:
            errors.append("max_tweet_age_hours should not exceed 24 for relevance")
        
        # Validate rate limits are not too aggressive
        if self.config.rate_limits.twitter_read_per_15min > 300:
            errors.append("twitter_read_per_15min exceeds API limit of 300")
        
        if self.config.rate_limits.twitter_write_per_15min > 300:
            errors.append("twitter_write_per_15min exceeds API limit of 300")
        
        if self.config.rate_limits.perplexity_per_hour > 600:
            errors.append("perplexity_per_hour exceeds typical API limit of 600")
        
        return errors
    
    def save_config(self, config_path: Optional[str] = None) -> None:
        """Save current configuration to file (excluding API credentials)."""
        if not self.config:
            raise ValueError("No configuration loaded to save")
        
        save_path = config_path or self.config_path
        
        # Create config dict without API credentials
        config_dict = {
            'selection': self.config.selection.dict(),
            'reply': self.config.reply.dict(),
            'rate_limits': self.config.rate_limits.dict(),
            'app': self.config.app.dict()
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_config() -> Config:
    """Load and return application configuration."""
    return get_config_manager().load_config()


def validate_config() -> list[str]:
    """Validate current configuration and return errors."""
    return get_config_manager().validate_config()
