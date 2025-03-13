from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class GmailLabels:
    def __init__(self, service, config):
        self.service = service
        self.config = config

    def fetch_labels(self) -> List[Dict]:
        """
        Fetches labels from Gmail. First tries to get user-defined labels,
        falls back to config labels if no user labels exist.
        """
        try:
            # Always try to get user labels first
            results = self.service.users().labels().list(userId='me').execute()
            user_labels = [
                label for label in results.get('labels', [])
                if label['type'] == 'user'
            ]

            if user_labels:
                logger.info(f"Found {len(user_labels)} user-defined labels")
                return user_labels
            
            # If no user labels found, fall back to config labels
            if self.config and hasattr(self.config, 'email_labels'):
                logger.info("No user labels found, using default labels from config")
                return [{'name': label, 'type': 'user'} for label in self.config.email_labels]
            
            # If no labels found anywhere
            logger.warning("No labels found in Gmail or config")
            return []

        except Exception as e:
            logger.error(f"Error fetching labels: {str(e)}")
            return []
        
    def update_labels(self, email_info, classifications):
        """Apply the classified labels to the emails"""
        # Get all labels from Gmail
        available_labels = self.fetch_labels()

        for email_data, (subject, label) in zip(email_info, classifications):
            if label:
                if label == 'NONE':
                    logger.info(f"Skipping email: {subject} as label is NONE")
                    continue
                message_id = email_data['id']
                success = self._update_label(message_id, label, available_labels)
                if success:
                    logger.info(f"Applied label '{label}' to email: {subject}")
                else:
                    logger.error(f"Failed to apply label '{label}' to email: {subject}")        

    def _update_label(self, message_id: str, label_name: str, available_labels: List[Dict]) -> bool:
        """Applies a label to an email. Creates the label if it doesn't exist."""
        try:            
            # Get all labels to find or create the desired label
            labels = available_labels
            label_id = None

            # Look for existing label
            for label in labels:
                if label['name'].lower() == label_name.lower() and label['id'] is not None:
                    label_id = label['id']
                    break

            # Create new label if it doesn't exist
            if not label_id:
                logger.info(f"Creating new label: {label_name}")
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
            logger.error(f'Error applying label: {e}')
            return False
