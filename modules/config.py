import os
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from modules.logging import setup_logging

logger = setup_logging()

# --- Pydantic Models for Config Structure ---

class DefaultsConfig(BaseModel):
    llm_provider: str
    llm_model: str
    max_emails: int
    days_old: int
    dry_run: bool
    save_steps: bool
    use_full_content: bool
    print_output: bool = Field(alias='print')

class ModelConfig(BaseModel):
    model_type: Optional[str] = 'standard'
    reasoning_effort: Optional[str] = 'medium'
    temperature: Optional[float] = 0.1
    top_p: Optional[float] = 0.1
    max_tokens: Optional[int] = 500

class ProviderConfig(BaseModel):
    models: Dict[str, ModelConfig]

class RootConfig(BaseModel):
    defaults: DefaultsConfig
    llm_providers: Dict[str, ProviderConfig]
    email_labels: List[str]

# --- Config Class ---

class Config:
    settings: RootConfig # Add type hint for the parsed settings

    def __init__(self):
        load_dotenv()
        self.load_config()
        
    def load_config(self):
        """Load configuration from YAML file and parse with Pydantic."""
        config_path = Path('config/config.yaml')
        logger.info(f"Loading configuration from: {config_path}")
        if not config_path.is_file():
            logger.error(f"Configuration file not found at {config_path}")
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        try:
            with open(config_path) as f:
                raw_config = yaml.safe_load(f)
            
            # Parse the raw dictionary using the RootConfig model
            self.settings = RootConfig.model_validate(raw_config)
            logger.info("Configuration loaded and validated successfully.")

        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {config_path}: {e}")
            raise RuntimeError(f"Failed to parse config YAML: {e}") from e
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            # Optionally print more details from e.errors()
            raise RuntimeError(f"Invalid configuration structure: {e}") from e
        except Exception as e:
            logger.error(f"An unexpected error occurred loading config: {e}")
            raise RuntimeError(f"Failed to load config: {e}") from e
            
    # --- Accessor methods using self.settings --- 
            
    @property
    def default_provider(self) -> str:
        """Get default LLM provider"""
        return self.settings.defaults.llm_provider
        
    @property
    def default_model(self) -> str:
        """Get default LLM model"""
        return self.settings.defaults.llm_model
        
    @property
    def max_emails(self) -> int:
        """Get default maximum emails to process"""
        return self.settings.defaults.max_emails
        
    @property
    def days_old(self) -> int:
        """Get default days to look back"""
        return self.settings.defaults.days_old

    @property
    def dry_run(self) -> bool:
        """Get default dry run setting"""
        return self.settings.defaults.dry_run

    @property
    def use_full_content(self) -> bool:
        """Get setting for using full email content vs snippet"""
        return self.settings.defaults.use_full_content
        
    @property
    def print_output(self) -> bool:
        """Get setting for printing output to console"""
        return self.settings.defaults.print_output
    
    @property
    def save_steps(self) -> bool:
        """Get setting for saving steps to file"""
        return self.settings.defaults.save_steps
        
    def get_provider_models(self, provider: str) -> Dict[str, ModelConfig]:
        """Get dictionary of models available for a provider."""
        provider_config = self.settings.llm_providers.get(provider)
        if not provider_config:
            # Log error instead of raising ValueError immediately?
            logger.error(f"Configuration for provider '{provider}' not found.")
            raise ValueError(f"Invalid or missing provider in config: {provider}")
        return provider_config.models
        
    def validate_model(self, provider: str, model: str) -> bool:
        """Validate if a model is available for a provider."""
        try:
            provider_models = self.get_provider_models(provider)
            return model in provider_models
        except ValueError: # Catch error from get_provider_models if provider invalid
            return False

    def get_model_config(self, provider: str, model: str) -> dict:
        """Get the detailed configuration for a specific model as a dict."""
        try:
            provider_models = self.get_provider_models(provider)
            model_config_obj = provider_models.get(model)
            
            if model_config_obj:
                # Return as dictionary for compatibility with LLMProcessor
                # Use include/exclude or other model_dump options if needed
                return model_config_obj.model_dump(exclude_none=True) 
            else:
                logger.warning(f"Model '{model}' not found under provider '{provider}'. Returning default model settings.")
                # Return the dictionary representation of a default ModelConfig instance
                return ModelConfig().model_dump(exclude_none=True)
        except ValueError: # Catch error from get_provider_models if provider invalid
            logger.warning(f"Provider '{provider}' not found when getting config for model '{model}'. Returning empty config.")
            return {} # Return empty dict if provider invalid

    @property
    def email_labels(self) -> List[str]:
        """Get list of email labels to process"""
        return self.settings.email_labels 