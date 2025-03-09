import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class OutputWriter:
    def __init__(self, output_dir='outputs'):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def write_results(self, email_info, classifications, print_to_console=False):
        """Write classification and summarization results to file and optionally console"""
        logger.info("Saving results")
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d%H%M')
        output_file = os.path.join(self.output_dir, f'output-{timestamp}.txt')
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write summarization results
                f.write("Summarization Results:\n")
                for email in email_info:
                    summary_text = self._format_summary(email)
                    f.write(summary_text)
                    if print_to_console:
                        print(summary_text)

                # Write classification results
                f.write("\nClassification Results:\n")
                for subject, label in classifications:
                    classification_text = self._format_classification(subject, label)
                    f.write(classification_text)
                    if print_to_console:
                        print(classification_text)

            logger.info(f"Results written to: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Error writing results to file: {e}")
            raise

    def _format_summary(self, email):
        """Format a single email summary"""
        return (f"\nDate: {email['date']}\n"
                f"Email: {email['subject']}\n"
                f"Summary: {email['summary']}\n")

    def _format_classification(self, subject, label):
        """Format a single classification result"""
        return f"\nEmail: {subject}\nSuggested Label: {label}\n" 