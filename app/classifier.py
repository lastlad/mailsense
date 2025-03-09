import os
import sys
import logging
import argparse
from dotenv import load_dotenv
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

class EmailClassifier:
    def __init__(self, args):
        self.args = args
        logger.info("Initializing EmailClassifier")
        self.service = GmailAuth.get_gmail_service()
        self.output_writer = OutputWriter()
        self.labels_manager = GmailLabels(self.service)
        self.email_processor = EmailProcessor(self.service)
        
        # Initialize LLM processors using either specific or default settings
        self.summary_llm = LLMProcessor(
            provider=args.summary_provider or args.provider,
            model_name=args.summary_model or args.model
        )
        
        # Use the same LLM instance if no specific classification settings provided
        if not any([args.classify_provider, args.classify_model]):
            logger.info("Using same LLM for classification and summarization")
            self.classify_llm = self.summary_llm
        else:
            logger.info("Using separate LLM for classification")
            self.classify_llm = LLMProcessor(
                provider=args.classify_provider or args.provider,
                model_name=args.classify_model or args.model
            )

    def run(self):
        try:
            logger.info("Starting email classification process")

            # Process emails
            logger.info(f"Fetching up to {self.args.max_emails} unread emails")
            email_info = self.email_processor.get_unread_emails(self.args)
            self.output_writer.save_step_output(
                email_info, 
                'emails',
                print_to_console=self.args.print
            )

            # Summarize emails using summary LLM
            logger.info("Summarizing emails")
            email_info = self.summary_llm.summarize_emails(self.args, email_info)
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
    parser = argparse.ArgumentParser(description='email classifier')
    
    # Common LLM arguments
    parser.add_argument(
        '--provider', 
        default='openai',
        choices=['openai','bedrock','ollama','anthropic','huggingface'],
        help='Default LLM provider to use. Can be overridden by --summary-provider or --classify-provider'
    )
    parser.add_argument(
        '--model', 
        default='gpt-4o-mini',
        choices=['gpt-4o-mini','gpt-4o','claude-sonnet-35','claude-haiku-35','llama-33-70B', 'deepseek-r1:7b'],
        help='Default LLM Model to use. Can be overridden by --summary-model or --classify-model'
    )

    # Optional separate summarization LLM arguments
    parser.add_argument(
        '--summary-provider', 
        default=None,
        choices=['openai','bedrock','ollama','anthropic','huggingface'],
        help='Override: LLM provider to use for summarization.'
    )
    parser.add_argument(
        '--summary-model', 
        default=None,
        choices=['gpt-4o-mini','gpt-4o','claude-sonnet-35','claude-haiku-35','llama-33-70B', 'deepseek-r1:7b'],
        help='Override: LLM Model to use for summarization.'
    )

    # Optional separate classification LLM arguments
    parser.add_argument(
        '--classify-provider', 
        default=None,
        choices=['openai','bedrock','ollama','anthropic','huggingface'],
        help='Override: LLM provider to use for classification.'
    )
    parser.add_argument(
        '--classify-model', 
        default=None,
        choices=['gpt-4o-mini','gpt-4o','claude-sonnet-35','claude-haiku-35','llama-33-70B', 'deepseek-r1:7b'],
        help='Override: LLM Model to use for classification.'
    )

    # Existing arguments...
    parser.add_argument(
        '--llm-api-keys',
        type=str,
        required=False,
        help='API Keys for the LLM provider of choice. Loads from .env if not provided.'
    )
    # parser.add_argument(
    #     '--only-unread', 
    #     type=bool, 
    #     default=True,
    #     help='Label on the unread emails. *** Be cautious as labelling all emails will be expensive.'
    # )
    #TODO: Refactor to use `action` instead of type.
    parser.add_argument(
        '--skip-user-labels',
        type=bool,
        default=False,
        help='Skip using existing user defined labels to classify emails. By default, user labels will be used.'
    )
    parser.add_argument(
        '--create-labels', 
        type=bool, 
        default=False,
        help='Create new labels on the fly using LLM. If not, will look for a correct fit from the available labels.'
    )
    parser.add_argument(
        '--dry-run', 
        type=bool, 
        default=True,
        help='Dry run. Will not update the labels of the emails.'
    )
    parser.add_argument(
        '--max-emails', 
        type=int, 
        default=15,
        required=False,
        help='Maximum number of unread emails to process (default: 25)'
    )
    parser.add_argument(
        '--days-old', 
        type=int, 
        default=2,
        required=False,
        help='Maximum number of look back days for fetching the emails. (E.g: Last 7 days.)'
    )
    parser.add_argument(
        '--start-date', 
        type=str, 
        required=False,
        help='Start Date for the email fetch in YYYY-MM-DD format.'
    )
    parser.add_argument(
        '--end-date', 
        type=str, 
        required=False,
        help='End Date for the email fetch in YYYY-MM-DD format.'
    )
    parser.add_argument(
        '--use-email-content', 
        action='store_false', 
        help='If set, will also uses the contents of the email to get additional context about the email. WARNING: Will result in additional LLM Token costs.'
    )
    parser.add_argument(
        '--print', 
        action='store_true',
        help='Print results to console in addition to saving to file'
    )

    args = parser.parse_args()
    
    labeller = EmailClassifier(args)
    labeller.run()