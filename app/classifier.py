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
        self.args = args
        
        # Use config with argument overrides
        self.args.max_emails = args.max_emails or self.config.max_emails
        self.args.days_old = args.days_old or self.config.days_old
        
        # Set defaults for boolean flags from config if not explicitly set
        if not hasattr(self.args, 'skip_user_labels'):
            self.args.skip_user_labels = self.config.skip_user_labels
        if not hasattr(self.args, 'create_labels'):
            self.args.create_labels = self.config.create_labels
        if not hasattr(self.args, 'dry_run'):
            self.args.dry_run = self.config.dry_run
        
        # Validate date arguments
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
        
        # Initialize LLMs with config defaults or overrides
        provider = self.config.default_provider
        summary_model = args.summary_model or self.config.default_model
        classify_model = args.classify_model or self.config.default_model

        # Validate models
        if not self.config.validate_model(provider, summary_model):
            raise ValueError(f"Invalid model {summary_model} for provider {provider}")
        if not self.config.validate_model(provider, classify_model):
            raise ValueError(f"Invalid model {classify_model} for provider {provider}")
        
        logger.info(f"Using provider: {provider}")
        logger.info(f"Summary model: {summary_model}")
        logger.info(f"Classification model: {classify_model}")

        # Initialize LLM processors
        self.summary_llm = LLMProcessor(
            provider=provider,
            model_name=summary_model
        )
        
        # Use the same LLM instance if models are the same
        if summary_model == classify_model:
            logger.info("Using same LLM for classification and summarization")
            self.classify_llm = self.summary_llm
        else:
            logger.info("Using separate LLM for classification")
            self.classify_llm = LLMProcessor(
                provider=provider,
                model_name=classify_model
            )

        logger.info("Initializing EmailClassifier")
        self.service = GmailAuth.get_gmail_service()
        self.output_writer = OutputWriter()
        self.labels_manager = GmailLabels(self.service)
        self.email_processor = EmailProcessor(self.service)

    def run(self):
        try:
            logger.info("Starting email classification process")

            # Process emails
            logger.info(f"Fetching up to {self.args.max_emails} unread emails")
            email_info = self.email_processor.get_unread_emails(self.args)
            if self.args.save_steps:
                self.output_writer.save_step_output(
                    email_info, 
                    'emails',
                    print_to_console=self.args.print
                )

            # Summarize emails using summary LLM
            logger.info("Summarizing emails")
            email_info = self.summary_llm.summarize_emails(self.args, email_info)
            if self.args.save_steps:
                self.output_writer.save_step_output(
                    email_info, 
                    'summaries',
                    print_to_console=self.args.print
                )

            # Get labels if needed
            all_labels = []
            if not self.args.skip_user_labels:
                logger.info("Fetching user labels")
                all_labels = self.labels_manager.list_user_labels()

            # Classify emails using classification LLM
            logger.info("Classifying emails")
            classifications = self.classify_llm.classify_emails(self.args, email_info, all_labels)
            
            # Always save final classifications
            self.output_writer.save_step_output(
                classifications, 
                'classifications',
                print_to_console=self.args.print
            )

            # Apply labels if not in dry run mode
            if not self.args.dry_run:
                logger.info("Applying labels to emails")
                self.labels_manager.update_labels(email_info, classifications)
            else:
                logger.info("Dry run.... Not Modifying the labels of email.")

        except Exception as e:
            logger.error(f"Error in run method: {str(e)}")
            raise

if __name__ == '__main__':
    logger.info("Starting email classifier application")
    parser = argparse.ArgumentParser(description='Gmail Email Classifier')
    
    # Core functionality arguments
    parser.add_argument(
        '--max-emails', 
        type=int,
        help='Override default: Maximum number of emails to process'
    )

    # Date filtering arguments
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument(
        '--date-range',
        type=str,
        choices=['1d', '3d', '7d', '14d', '30d'],
        help='Process emails from last N days'
    )
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

    # LLM Selection (optional overrides)
    parser.add_argument(
        '--summary-model',
        help='Override: Specific model to use for summarization'
    )
    parser.add_argument(
        '--classify-model',
        help='Override: Specific model to use for classification'
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