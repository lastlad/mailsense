import os
import sys
import logging
from dotenv import load_dotenv
from datetime import datetime
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('classifier.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from modules.auth import GmailAuth
from modules.email import EmailProcessor
from modules.label import GmailLabels
from modules.llm import LLMProcessor
from modules.output import OutputWriter
from modules.config import Config

class EmailClassifier:
    def __init__(self, args):
        self.config = Config()
        self.args = self._initialize_args(args)
        
        # Initialize services and processors
        self.service = GmailAuth.get_gmail_service()
        self.output_writer = OutputWriter()
        self.labels_manager = GmailLabels(self.service, self.config)
        self.email_processor = EmailProcessor(self.service)
        
        # Initialize LLM processors
        self.summary_llm, self.classify_llm = self._setup_llm_processors()
        
        logger.info("EmailClassifier initialized successfully")

    def _initialize_args(self, args):
        """Initialize and validate command line arguments with config defaults"""
        # Set numeric defaults
        args.max_emails = args.max_emails or self.config.max_emails
        
        # Set boolean defaults
        self._set_boolean_defaults(args)
        
        # Validate date arguments
        self._validate_date_arguments(args)
        
        return args

    def _set_boolean_defaults(self, args):
        """Set boolean flags from config if not explicitly set"""
        boolean_flags = {
            'dry_run': self.config.dry_run,
            'use_full_content': self.config.use_full_content
        }
        
        for flag, default in boolean_flags.items():
            if not hasattr(args, flag):
                setattr(args, flag, default)

    def _validate_date_arguments(self, args):
        """Validate date-related arguments and set defaults based on priority:
        1. If date_from and date_to are provided, use them
        2. If days_old is provided, use it
        3. Fall back to days_old from config
        """
        # Check if date parameters are provided
        has_date_from = hasattr(args, 'date_from') and args.date_from is not None
        has_date_to = hasattr(args, 'date_to') and args.date_to is not None
        has_days_old = hasattr(args, 'days_old') and args.days_old is not None
        
        # Validate that date_from and date_to are used together
        if (has_date_from and not has_date_to) or (not has_date_from and has_date_to):
            raise ValueError("Both --date-from and --date-to must be provided together")
        
        # Validate that days_old is not used with date_from/date_to
        if has_days_old and (has_date_from or has_date_to):
            raise ValueError("--days-old cannot be used with --date-from or --date-to")
        
        # Apply priority logic for date filtering
        if has_date_from and has_date_to:
            # Priority 1: Use date range if provided
            logger.info(f"Using date range: {args.date_from} to {args.date_to}")
            # If days_old exists as an attribute but wasn't explicitly set, set it to None
            if hasattr(args, 'days_old'):
                args.days_old = None
        elif has_days_old:
            # Priority 2: Use days_old if provided
            logger.info(f"Using days_old: {args.days_old}")
        else:
            # Priority 3: Fall back to config default for days_old
            if not hasattr(args, 'days_old') or args.days_old is None:
                args.days_old = self.config.days_old
                logger.info(f"Using default days_old from config: {args.days_old}")

    def _setup_llm_processors(self):
        """Initialize and validate LLM processors"""
        provider = self.config.default_provider
        
        # If not using full content, we only need one LLM for classification
        if not self.args.use_full_content:
            model = self.args.classify_model or self.config.default_model
            if not self.config.validate_model(provider, model):
                raise ValueError(f"Invalid model {model} for provider {provider}")
            
            logger.info(f"Using provider: {provider}")
            logger.info(f"Classification model: {model}")
            
            # Use same instance for both since summarization will be skipped
            llm = LLMProcessor(provider=provider, model_name=model)
            return llm, llm
        
        # If using full content, set up both processors if needed
        summary_model = self.args.summary_model or self.config.default_model
        classify_model = self.args.classify_model or self.config.default_model

        # Validate models
        for model in [summary_model, classify_model]:
            if not self.config.validate_model(provider, model):
                raise ValueError(f"Invalid model {model} for provider {provider}")
        
        logger.info(f"Using provider: {provider}")
        logger.info(f"Summary model: {summary_model}")
        logger.info(f"Classification model: {classify_model}")

        # Initialize summary LLM
        summary_llm = LLMProcessor(
            provider=provider,
            model_name=summary_model
        )
        
        # Use same LLM instance if models are identical
        if summary_model == classify_model:
            logger.info("Using same LLM for classification and summarization")
            classify_llm = summary_llm
        else:
            logger.info("Using separate LLM for classification")
            classify_llm = LLMProcessor(
                provider=provider,
                model_name=classify_model
            )
            
        return summary_llm, classify_llm

    def run(self):
        """Main execution method"""
        try:
            logger.info("Starting email classification process")
            
            # Process and classify emails
            email_info = self._process_emails()
            classifications = self._classify_emails(email_info)
            
            # Apply labels if not in dry run mode
            if self.args.dry_run:
                logger.info("Dry run.... Not Modifying the labels of email.")
            else:
                logger.info("Applying labels to emails")
                self.labels_manager.update_labels(email_info, classifications)

        except Exception as e:
            logger.error(f"Error in run method: {str(e)}")
            raise

    def _process_emails(self):
        """Process and summarize emails"""
        # Fetch emails
        logger.info(f"Fetching up to {self.args.max_emails} unread emails")
        email_info = self.email_processor.get_unread_emails(self.args)
        if self.args.save_steps:
            self.output_writer.save_step_output(
                email_info, 
                'emails',
                print_to_console=self.args.print
            )

        # Only summarize if using full content
        if self.args.use_full_content:
            logger.info("Summarizing emails")
            email_info = self.summary_llm.summarize_emails(self.args, email_info)
            if self.args.save_steps:
                self.output_writer.save_step_output(
                    email_info, 
                    'summaries',
                    print_to_console=self.args.print
                )
        else:
            logger.info("Using email snippets directly for classification")
            # Add summary structure using the snippet
            for email in email_info:
                email['summary'] = {
                    'summary': email['content'],  # content is already the snippet
                    'category_major': '',
                    'category_minor': '',
                    'category_reasoning': ''
                }

        return email_info

    def _classify_emails(self, email_info):
        """Classify emails using LLM"""
        # Get labels
        logger.info("Fetching labels")
        all_labels = self.labels_manager.fetch_labels()

        # Classify emails
        logger.info("Classifying emails")
        classifications = self.classify_llm.classify_emails(
            self.args, 
            email_info, 
            all_labels
        )
        
        # Always save final classifications
        self.output_writer.save_step_output(
            classifications, 
            'classifications',
            print_to_console=self.args.print
        )
        
        return classifications