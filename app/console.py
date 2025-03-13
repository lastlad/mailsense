import argparse
import logging
from classifier import EmailClassifier

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

def create_arg_parser():
    """Create and return the argument parser"""
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
        help='Use full email content instead of just snippet for classification'
    )

    # LLM Selection
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
        '--use-user-labels',
        action='store_true',
        help='Use Gmail account labels instead of predefined labels'
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

    return parser

def run_console():
    """Run the application in console mode"""
    parser = create_arg_parser()
    args = parser.parse_args()
    
    logger.info("Starting MailSense - email classifier application")
    labeller = EmailClassifier(args)
    labeller.run()

if __name__ == '__main__':
    run_console() 