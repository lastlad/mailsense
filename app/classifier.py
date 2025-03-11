import os
import sys
import logging
import argparse
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
        self.labels_manager = GmailLabels(self.service)
        self.email_processor = EmailProcessor(self.service)
        
        # Initialize LLM processors
        self.summary_llm, self.classify_llm = self._setup_llm_processors()
        
        logger.info("EmailClassifier initialized successfully")

    def _initialize_args(self, args):
        """Initialize and validate command line arguments with config defaults"""
        # Set numeric defaults
        args.max_emails = args.max_emails or self.config.max_emails
        args.days_old = args.days_old or self.config.days_old
        
        # Set boolean defaults
        self._set_boolean_defaults(args)
        
        # Validate date arguments
        self._validate_date_args(args)
        
        return args

    def _set_boolean_defaults(self, args):
        """Set boolean flags from config if not explicitly set"""
        boolean_flags = {
            'skip_user_labels': self.config.skip_user_labels,
            'create_labels': self.config.create_labels,
            'dry_run': self.config.dry_run,
            'use_full_content': self.config.use_full_content
        }
        
        for flag, default in boolean_flags.items():
            if not hasattr(args, flag):
                setattr(args, flag, default)

    def _validate_date_args(self, args):
        """Validate date-related arguments"""
        if args.date_from and not args.date_to:
            raise ValueError("--date-to is required when using --date-from")
        if args.date_to and not args.date_from:
            raise ValueError("--date-from is required when using --date-to")
        
        if args.date_from and args.date_to:
            try:
                datetime.strptime(args.date_from, '%Y-%m-%d')
                datetime.strptime(args.date_to, '%Y-%m-%d')
            except ValueError:
                raise ValueError("Dates must be in YYYY-MM-DD format")

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
            if not self.args.dry_run:
                logger.info("Applying labels to emails")
                self.labels_manager.update_labels(email_info, classifications)
            else:
                logger.info("Dry run.... Not Modifying the labels of email.")

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
        # Get labels if needed
        all_labels = []
        if not self.args.skip_user_labels:
            logger.info("Fetching user labels")
            all_labels = self.labels_manager.list_user_labels()

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

if __name__ == '__main__':
    logger.info("Starting MailSense - email classifier application")
    parser = argparse.ArgumentParser(description='MailSense - Email Classifier')
    
    # Core functionality arguments
    parser.add_argument(
        '--max-emails', 
        type=int,
        help='Override default: Maximum number of emails to process'
    )

    # Date filtering arguments
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument(
        '--days-old',
        type=int,
        help='Override default: Process emails from last N days'
    )
    date_group.add_argument(
        '--date-from',
        type=str,
        help='Process emails from this date (YYYY-MM-DD). Use with --date-to'
    )
    date_group.add_argument(
        '--date-to',
        type=str,
        help='Process emails until this date (YYYY-MM-DD). Use with --date-from'
    )

    # Email content control
    parser.add_argument(
        '--use-full-content',
        action='store_true',
        help='Use full email content instead of just snippet for classification (may increase API costs)'
    )

    # LLM Selection (optional overrides)
    parser.add_argument(
        '--summary-model',
        help='Override: Specific model to use for summarization'
    )
    parser.add_argument(
        '--classify-model',
        help='Override: Specific model to use for classification'
    )

    # Label handling arguments
    parser.add_argument(
        '--skip-user-labels',
        action='store_true',
        help='Skip using existing user labels for classification'
    )
    parser.add_argument(
        '--create-labels',
        action='store_true',
        help='Allow creation of new labels'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without applying labels'
    )

    # Output control
    parser.add_argument(
        '--save-steps',
        action='store_true',
        help='Save intermediate outputs'
    )
    parser.add_argument(
        '--print',
        action='store_true',
        help='Print results to console'
    )

    args = parser.parse_args()
    
    labeller = EmailClassifier(args)
    labeller.run()