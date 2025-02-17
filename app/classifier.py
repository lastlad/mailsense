import os
import sys
import logging
import argparse
from datetime import datetime
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

class EmailClassifier:
    def __init__(self, args):
        self.args = args
        logger.info("Initializing EmailClassifier")
        self.service = GmailAuth.get_gmail_service()
        self.labels_manager = GmailLabels(self.service)
        self.email_processor = EmailProcessor(self.service)
        self.llm_processor = LLMProcessor(self.args)

    def run(self):
        logger.info("Starting email classification process")

        # Process emails
        logger.info(f"Fetching up to {self.args.max_emails} unread emails")
        email_info = self.email_processor.get_unread_emails(self.args)

        # Summarizing emails
        logger.info("Summarizing emails")
        email_info = self.llm_processor.summarize_emails(self.args, email_info)

        logger.info("Classifying emails")

        # Get labels if needed
        all_labels = []
        if self.args.use_user_labels:
            logger.info("Fetching user labels")
            all_labels = self.labels_manager.list_user_labels()

        classifications = self.llm_processor.classify_emails(self.args, email_info, all_labels)
        # classifications = []

        # Save results
        self._save_results(email_info, classifications)

    def _save_results(self, email_info, classifications):
        logger.info("Saving results")
        # Create outputs directory if it doesn't exist
        os.makedirs('outputs', exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        output_file = f'outputs/output-{timestamp}.txt'
        
        # Write results to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("Summarization Results:\n")
                for email in email_info:
                    f.write(f"\nDate: {email['date']}\n")
                    f.write(f"Email: {email['subject']}\n")
                    f.write(f"Summary: {email['summary']}\n")
                    # Print to console if --print flag is used
                    if self.args.print:
                        print(f"\nDate: {email['date']}")
                        print(f"Email: {email['subject']}")
                        print(f"Summary: {email['summary']}")

                f.write("\nClassification Results:\n")
                for subject, label in classifications:
                    f.write(f"\nEmail: {subject}\n")
                    f.write(f"Suggested Label: {label}\n")
                    # Print to console if --print flag is used
                    if self.args.print:
                        print(f"\nEmail: {subject}")
                        print(f"Suggested Label: {label}")

            logger.info(f"Results written to: {output_file}")
        except Exception as e:
            logger.error(f"Error writing results to file: {e}")
            raise

if __name__ == '__main__':
    logger.info("Starting email classifier application")
    # Set up argument parser
    parser = argparse.ArgumentParser(description='email classifier')
    parser.add_argument(
        '--provider', 
        default='openai',
        required=False,
        choices=['openai','bedrock','ollama','anthropic','huggingface'],
        help='LLM provider to use.'
    )
    parser.add_argument(
        '--model-name', 
        default='gpt-4o-mini',
        required=False,
        choices=['gpt-4o-mini','gpt-4o','claude-sonnet-35','claude-haiku-35','llama-33-70B', 'deepseek-r1:7b'],
        help='LLM Model to use.'
    )
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
    parser.add_argument(
        '--use-user-labels',
        action='store_true',
        help='Use existing user defined labels to classify the email. If none of the lables match, its marked as NONE.'
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