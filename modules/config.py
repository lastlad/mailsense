import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        self.load_config()
        
    def load_config(self):
        """Load configuration from YAML file"""
        config_path = Path('config/config.yaml')
        try:
            with open(config_path) as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config from {config_path}: {str(e)}")
            
    @property
    def default_provider(self) -> str:
        """Get default LLM provider"""
        return self.config['defaults']['llm_provider']
        
    @property
    def default_model(self) -> str:
        """Get default LLM model"""
        return self.config['defaults']['llm_model']
        
    @property
    def max_emails(self) -> int:
        """Get default maximum emails to process"""
        return self.config['defaults']['max_emails']
        
    @property
    def days_old(self) -> int:
        """Get default days to look back"""
        return self.config['defaults']['days_old']

    @property
    def dry_run(self) -> bool:
        """Get default dry run setting"""
        return self.config['defaults']['dry_run']

    @property
    def skip_user_labels(self) -> bool:
        """Get default skip user labels setting"""
        return self.config['defaults']['skip_user_labels']

    @property
    def create_labels(self) -> bool:
        """Get default create labels setting"""
        return self.config['defaults']['create_labels']
        
    def get_provider_models(self, provider: str) -> List[str]:
        """Get list of models available for a provider"""
        try:
            return self.config['llm_providers'][provider]['models']
        except KeyError:
            raise ValueError(f"Invalid provider: {provider}")
        
    def validate_model(self, provider: str, model: str) -> bool:
        """Validate if a model is available for a provider"""
        try:
            return model in self.get_provider_models(provider)
        except ValueError:
            return False

    @property
    def email_categories(self) -> List[str]:
        """Get list of email categories to process"""
        return self.config['email_categories'] 