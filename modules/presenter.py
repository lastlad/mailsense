from datetime import datetime
from tabulate import tabulate
from typing import List, Dict, Tuple, Any
from modules.logging import setup_logging

logger = setup_logging()

class ConsolePresenter:
    """Handles formatting and printing data to the console."""

    def display_classification_summary(self,
                                       email_info: List[Dict[str, Any]],
                                       classifications: List[Tuple[str, str]],
                                       subject_width: int = 50,
                                       snippet_width: int = 100):
        """
        Displays the classification summary in a formatted table.

        Args:
            email_info: List of dictionaries containing email details.
            classifications: List of tuples (subject, label).
            subject_width: Target width for the Subject column.
            snippet_width: Target width for the Snippet column.
        """

        print("\n=== CLASSIFICATION SUMMARY ===")

        if not email_info or not classifications:
             print("No classification data to display.")
             return

        table_data = []
        for email_data, (subject, label) in zip(email_info, classifications):
            timestamp_str = email_data.get('date', 'N/A')
            # Parse timestamp for sorting
            try:
                timestamp_dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                timestamp_dt = datetime.min 
                timestamp_str = f"{timestamp_str} (unparseable)"

            # Truncate or pad subject
            if len(subject) > subject_width:
                padded_subject = subject[:subject_width-3] + '...'
            else:
                padded_subject = subject.ljust(subject_width)

            # Truncate or pad snippet
            snippet = email_data.get('snippet', 'N/A')
            if len(snippet) > snippet_width:
                padded_snippet = snippet[:snippet_width-3] + '...'
            else:
                padded_snippet = snippet.ljust(snippet_width)

            table_data.append([timestamp_dt, timestamp_str, padded_subject, padded_snippet, label])

        # Sort by parsed datetime (first element), descending
        table_data.sort(key=lambda row: row[0], reverse=True)

        if table_data:
            headers = ["Timestamp", "Subject", "Snippet", "Proposed Label"]
            # Prepare data for tabulate (remove datetime object)
            display_data = [[row[1], row[2], row[3], row[4]] for row in table_data]
            print(tabulate(display_data, headers=headers, tablefmt="grid"))
        else:
            # This case might be redundant due to the initial check, but kept for safety
            print("No classifications to display after processing.") 