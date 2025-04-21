import os
import sys
from dotenv import load_dotenv
load_dotenv()

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from modules.clients.gmail_client import GmailClient
from modules.llm import LLMProcessor
from modules.output import OutputWriter
from modules.config import Config
from modules.logging import setup_logging
from modules.presenter import ConsolePresenter

# Configure logging
logger = setup_logging()

class EmailClassifier:
    def __init__(self, args):
        self.config = Config()
        self.args = self._initialize_args(args)
        
        # Initialize services and processors
        self.gmail_client = GmailClient(config=self.config)
        self.output_writer = OutputWriter()
        self.presenter = ConsolePresenter()
        
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
        
        # Determine classify model (always needed)
        classify_model_name = self.args.classify_model or self.config.default_model
        if not self.config.validate_model(provider, classify_model_name):
            raise ValueError(f"Invalid classify model {classify_model_name} for provider {provider}")
        
        logger.info(f"Using provider: {provider}")
        logger.info(f"Classification model: {classify_model_name}")
        
        # Initialize classify LLM first
        classify_llm = LLMProcessor(provider=provider, model_name=classify_model_name)
        
        # If not using full content, summary LLM is the same as classify LLM
        if not self.args.use_full_content:
            logger.info("Not using full content, summarization step will be skipped (using snippets).")
            return classify_llm, classify_llm
        
        # If using full content, determine and set up summary LLM
        summary_model_name = self.args.summary_model or self.config.default_model
        if not self.config.validate_model(provider, summary_model_name):
             raise ValueError(f"Invalid summary model {summary_model_name} for provider {provider}")
        
        logger.info(f"Summary model: {summary_model_name}")

        # Initialize summary LLM
        if summary_model_name == classify_model_name:
            logger.info("Using same LLM for classification and summarization.")
            summary_llm = classify_llm
        else:
            logger.info("Using separate LLM for summarization.")
            summary_llm = LLMProcessor(provider=provider, model_name=summary_model_name)
            
        return summary_llm, classify_llm

    def run(self):
        """Main execution method"""
        try:
            logger.info("Starting email classification process")
            
            # Process and classify emails
            email_info = self._process_emails()
            if not email_info:
                 logger.info("No emails found or processed. Exiting.")
                 return # Exit early if no emails
                 
            classifications = self._classify_emails(email_info)
            
            # Print summary table if requested using the presenter
            if self.args.print:
                self.presenter.display_classification_summary(email_info, classifications)

            # Apply labels if not in dry run mode
            if self.args.dry_run:
                logger.info("Dry run mode enabled. No labels will be applied.")
            else:
                logger.info("Applying labels to emails...")
                applied_count = 0
                for email_data, (subject, label) in zip(email_info, classifications):
                     if label and label != 'NONE':
                        message_id = email_data['id']
                        success = self.gmail_client.apply_label(message_id, label)
                        if success:
                            logger.info(f"Successfully applied label '{label}' to email: {subject}")
                            applied_count += 1
                        else:
                            # Error logged within apply_label
                            logger.warning(f"Failed to apply label '{label}' to email: {subject}")
                     elif label == 'NONE':
                         logger.info(f"Skipping label application for email (classified as NONE): {subject}")
                     else: # Handle cases where classification might be missing or invalid
                          logger.warning(f"Invalid or missing label '{label}' for email: {subject}. Skipping application.")
                logger.info(f"Finished applying labels. {applied_count} labels applied.")

        except Exception as e:
            logger.error(f"An error occurred during the classification run: {str(e)}", exc_info=True) # Log traceback
            # Decide if you want to re-raise or handle gracefully
            # raise # Re-raise if caller should handle it

    def _process_emails(self):
        """Fetch and potentially summarize emails"""
        # Fetch emails using the new client method
        logger.info(f"Fetching emails matching criteria (max: {self.args.max_emails})")
        email_info = self.gmail_client.fetch_emails(self.args)
        
        if not email_info:
             logger.info("No emails returned from fetch_emails.")
             return []

        if self.args.save_steps:
            self.output_writer.save_step_output(
                email_info,
                'emails'
            )

        # Only summarize if using full content
        if self.args.use_full_content:
            logger.info("Summarizing emails using full content...")
            # Pass email_info directly, summary LLM handles content extraction
            email_info = self.summary_llm.summarize_emails(self.args, email_info) 
            if self.args.save_steps:
                self.output_writer.save_step_output(
                    email_info,
                    'summaries'
                )
        else:
            logger.info("Using email snippets directly for classification (no summarization).")
            # Ensure 'summary' structure exists, using the snippet (which is in 'content' from fetch_emails)
            for email in email_info:
                 if 'summary' not in email: # Avoid overwriting if somehow populated
                    email['summary'] = {
                        'summary': email.get('content', ''), # Use snippet stored in 'content'
                        'category_major': '', # Initialize fields
                        'category_minor': '',
                        'category_reasoning': ''
                    }

        return email_info

    def _classify_emails(self, email_info):
        """Classify emails using LLM"""
        # Get available labels from the new client method
        logger.info("Fetching available Gmail labels...")
        all_labels = self.gmail_client.list_labels()
        
        if not all_labels:
             logger.warning("No labels found in Gmail or config. Classification might be impaired.")
             # Proceed, but classification might yield generic results or fail if labels are mandatory for the prompt

        # Classify emails
        logger.info("Classifying emails using LLM...")
        classifications = self.classify_llm.classify_emails(
            self.args, 
            email_info, 
            all_labels # Pass the fetched labels
        )
        
        # Always save final classifications
        self.output_writer.save_step_output(
            classifications,
            'classifications'
        )
        
        return classifications