
from typing import List, Dict

class GmailLabels:
    def __init__(self, service):
        self.service = service

    def list_user_labels(self) -> List[Dict]:
        """Fetches all user-defined labels in the Gmail account."""
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            if not labels:
                print('No labels found.')
                return []

            # print('Labels:')
            # for label in labels:
            #     print(f"Name: {label['name']:<30} ID: {label['id']}, Type: {label['type']}")
            
            # Return only user defined labels are we don't want to categorize them into gmail predefined labels.
            return [label for label in labels if label['type'] == 'user']
        except Exception as e:
            print(f'An error occurred: {e}')
            return []
