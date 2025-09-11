"""
Configuration Manager - Central configuration service
Eliminates all hardcoded values throughout the system
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Centralized configuration management
    - Loads YAML configuration files
    - Supports environment variable overrides
    - Provides dot notation access
    - Caches loaded configurations
    """
    
    _instance = None
    _config: Dict[str, Any] = {}
    _loaded = False
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize configuration manager"""
        if not self._loaded:
            self._load_configurations()
            self._loaded = True
    
    def _load_configurations(self):
        """Load all configuration files"""
        config_dir = Path("config")
        
        # Configuration files to load in order
        config_files = [
            "system_config.yaml",
            "prompts_optimized.yaml",
            "scoring_rules.yaml",  # If exists
            "custom_config.yaml"   # For local overrides
        ]
        
        for config_file in config_files:
            file_path = config_dir / config_file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                        if data:
                            self._merge_config(data)
                            logger.info(f"Loaded configuration: {config_file}")
                except Exception as e:
                    logger.error(f"Failed to load {config_file}: {e}")
        
        # Apply environment variable overrides
        self._apply_env_overrides()
    
    def _merge_config(self, data: Dict[str, Any]):
        """Recursively merge configuration data"""
        for key, value in data.items():
            if key in self._config and isinstance(self._config[key], dict) and isinstance(value, dict):
                self._config[key] = {**self._config[key], **value}
            else:
                self._config[key] = value
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides"""
        # Handle specific environment variables
        env_mappings = {
            'SECRET_KEY': 'auth.secret_key',
            'DB_PATH': 'database.path',
            'LOG_LEVEL': 'logging.level',
            'AI_MODEL': 'ai_models.default_model'
        }
        
        for env_var, config_path in env_mappings.items():
            if env_value := os.getenv(env_var):
                self.set(config_path, env_value)
                logger.info(f"Override {config_path} from environment")
    
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            path: Dot-separated path (e.g., 'scoring.thresholds.severe')
            default: Default value if path not found
            
        Returns:
            Configuration value or default
        """
        keys = path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        # Handle environment variable placeholders
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.getenv(env_var, default)
        
        return value
    
    def set(self, path: str, value: Any):
        """
        Set configuration value at runtime
        
        Args:
            path: Dot-separated path
            value: Value to set
        """
        keys = path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section: Section name (e.g., 'scoring', 'auth')
            
        Returns:
            Configuration section as dictionary
        """
        return self._config.get(section, {})
    
    def reload(self):
        """Reload all configurations"""
        self._config = {}
        self._load_configurations()
        logger.info("Configuration reloaded")
    
    def validate(self) -> bool:
        """
        Validate configuration integrity
        
        Returns:
            True if configuration is valid
        """
        required_sections = ['auth', 'scoring', 'dialogue', 'ai_models']
        
        for section in required_sections:
            if section not in self._config:
                logger.error(f"Missing required configuration section: {section}")
                return False
        
        # Validate specific values
        if self.get('scoring.evidence.min_count_for_scoring', 0) <= 0:
            logger.error("Invalid min_count_for_scoring")
            return False
        
        if not 0 <= self.get('dialogue.dialogue_ratio', 0) <= 1:
            logger.error("Invalid dialogue_ratio")
            return False
        
        return True
    
    def get_feature_flag(self, flag: str) -> bool:
        """
        Get feature flag value
        
        Args:
            flag: Feature flag name
            
        Returns:
            Feature flag value (default False)
        """
        return self.get(f'features.{flag}', False)
    
    def get_error_message(self, category: str, key: str, **kwargs) -> str:
        """
        Get formatted error message
        
        Args:
            category: Error category (e.g., 'auth', 'validation')
            key: Error key
            **kwargs: Format parameters
            
        Returns:
            Formatted error message
        """
        message = self.get(f'errors.{category}.{key}', 'An error occurred')
        
        # Format message with parameters
        try:
            return message.format(**kwargs)
        except:
            return message


# Global configuration instance
config = ConfigManager()


def get_config() -> ConfigManager:
    """Get global configuration instance"""
    return config


def reload_config():
    """Reload configuration"""
    config.reload()