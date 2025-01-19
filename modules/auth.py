import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

class GmailAuth:
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

    @staticmethod
    def get_gmail_service():
        """Gets Gmail API service instance."""
        creds = None

        # Get the project root directory (assuming modules is directly under project root)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        token_path = os.path.join(project_root, 'token.json')
        creds_path = os.path.join(project_root, 'credentials.json')

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, GmailAuth.SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_path, GmailAuth.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)
