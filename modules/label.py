from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class GmailLabels:
    def __init__(self, service, config):
        self.service = service
        self.config = config

    def fetch_labels(self, use_user_labels) -> List[Dict]:
        """Fetches all labels from the Gmail account. If use_user_labels is True, it will fetch user defined labels from the Gmail account."""
        try:
            if not use_user_labels and self.config:
                # Use predefined labels from config
                return [{'name': label, 'type': 'user'} for label in self.config.email_labels]
            else:
                results = self.service.users().labels().list(userId='me').execute()
                labels = results.get('labels', [])

                if not labels:
                    print('No labels found.')
                    return []

                # Return only user defined labels are we don't want to categorize them into gmail predefined labels.
                return [label for label in labels if label['type'] == 'user']
        except Exception as e:
            print(f'An error occurred while fetching labels: {e}')
            return []
        
    def update_labels(self, email_info, classifications):
        """Apply the classified labels to the emails"""
        for email_data, (subject, label) in zip(email_info, classifications):
            if label:
                message_id = email_data['id']
                success = self._update_label(message_id, label)
                if success:
                    logger.info(f"Applied label '{label}' to email: {subject}")
                else:
                    logger.error(f"Failed to apply label '{label}' to email: {subject}")        

    def _update_label(self, message_id: str, label_name: str) -> bool:
        """Applies a label to an email. Creates the label if it doesn't exist."""
        try:            
            # Get all labels to find or create the desired label
            labels = self.fetch_labels()
            label_id = None

            # Look for existing label
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    label_id = label['id']
                    break

            # Create new label if it doesn't exist
            if not label_id:
                label_object = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
                created_label = self.service.users().labels().create(
                    userId='me',
                    body=label_object
                ).execute()
                label_id = created_label['id']

            # Apply the label to the email
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            return True
        except Exception as e:
            print(f'Error applying label: {e}')
            return False
