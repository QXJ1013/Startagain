"""
Configuration Manager for centralized config loading and access
Provides singleton pattern for efficient config management
"""

from typing import Dict, Any, Optional, Union
import yaml
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Singleton configuration manager that loads and caches YAML config files.
    Supports dot notation for nested value access.
    """
    
    _instance = None
    _configs: Dict[str, Dict[str, Any]] = {}
    _config_dir: Path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize configuration directory path"""
        # Try multiple possible config locations
        possible_paths = [
            Path("config"),                           # Running from backend/
            Path("backend/config"),                   # Running from project root
            Path(__file__).parent.parent.parent / "config",  # Relative to this file
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_dir():
                self._config_dir = path
                logger.info(f"Config directory found at: {path}")
                break
        
        if self._config_dir is None:
            # Create default config directory
            self._config_dir = Path("backend/config")
            self._config_dir.mkdir(parents=True, exist_ok=True)
            logger.warning(f"Config directory not found, created at: {self._config_dir}")
    
    def load_config(self, name: str, path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load and cache a configuration file.
        
        Args:
            name: Configuration name (without .yaml extension)
            path: Optional custom path to config file
            
        Returns:
            Dictionary containing configuration data
            
        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        # Check cache first
        if name in self._configs:
            return self._configs[name]
        
        # Determine config file path
        if path:
            config_path = Path(path)
        else:
            config_path = self._config_dir / f"{name}.yaml"
        
        # Check if file exists
        if not config_path.exists():
            # Try with .yml extension
            alt_path = self._config_dir / f"{name}.yml"
            if alt_path.exists():
                config_path = alt_path
            else:
                logger.error(f"Configuration file not found: {config_path}")
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        # Load YAML file
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # Cache the configuration
            self._configs[name] = config or {}
            logger.info(f"Loaded configuration: {name} from {config_path}")
            
            return self._configs[name]
            
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {config_path}: {e}")
            raise ValueError(f"Invalid YAML in {config_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., "selection.scoring.weights.keyword_exact_match")
            default: Default value if key not found
            
        Returns:
            Configuration value or default
            
        Examples:
            config.get("selection.scoring.weights.keyword_exact_match")
            config.get("selection.strategies", [])
        """
        keys = key.split('.')
        
        # First part should be the config name
        config_name = keys[0]
        
        # Load config if not already loaded
        if config_name not in self._configs:
            try:
                self.load_config(config_name)
            except FileNotFoundError:
                logger.warning(f"Config file '{config_name}' not found, returning default")
                return default
        
        # Navigate through nested structure
        value = self._configs.get(config_name, {})
        
        for k in keys[1:]:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default
    
    def get_config(self, name: str) -> Dict[str, Any]:
        """
        Get entire configuration dictionary.
        
        Args:
            name: Configuration name
            
        Returns:
            Complete configuration dictionary
        """
        if name not in self._configs:
            self.load_config(name)
        return self._configs.get(name, {})
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value (runtime only, doesn't persist to file).
        
        Args:
            key: Configuration key in dot notation
            value: Value to set
        """
        keys = key.split('.')
        config_name = keys[0]
        
        # Ensure config exists
        if config_name not in self._configs:
            self._configs[config_name] = {}
        
        # Navigate to the parent of the target key
        current = self._configs[config_name]
        for k in keys[1:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        # Set the value
        if len(keys) > 1:
            current[keys[-1]] = value
        else:
            self._configs[config_name] = value
            
        logger.debug(f"Set config value: {key} = {value}")
    
    def reload(self, name: Optional[str] = None) -> None:
        """
        Reload configuration(s) from disk.
        
        Args:
            name: Specific config to reload, or None to reload all
        """
        if name:
            if name in self._configs:
                del self._configs[name]
                self.load_config(name)
                logger.info(f"Reloaded configuration: {name}")
        else:
            # Reload all configs
            config_names = list(self._configs.keys())
            self._configs.clear()
            for config_name in config_names:
                self.load_config(config_name)
            logger.info(f"Reloaded all {len(config_names)} configurations")
    
    def clear_cache(self) -> None:
        """Clear all cached configurations"""
        self._configs.clear()
        logger.info("Cleared configuration cache")
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all loaded configurations"""
        return dict(self._configs)
    
    def is_loaded(self, name: str) -> bool:
        """Check if a configuration is loaded"""
        return name in self._configs


# Create singleton instance
config = ConfigManager()

# Convenience functions
def get_config(key: str, default: Any = None) -> Any:
    """Get configuration value using dot notation"""
    return config.get(key, default)

def load_config(name: str) -> Dict[str, Any]:
    """Load a configuration file"""
    return config.load_config(name)

def reload_config(name: Optional[str] = None) -> None:
    """Reload configuration(s)"""
    config.reload(name)