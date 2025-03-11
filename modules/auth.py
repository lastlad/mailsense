import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import pickle

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',  # Scope for reading
    'https://www.googleapis.com/auth/gmail.labels',    # Scope for label management
    'https://www.googleapis.com/auth/gmail.modify'     # Scope for modifying emails
]

class GmailAuth:
    @staticmethod
    def get_gmail_service():
        """Gets Gmail API service instance."""
        creds = None

        # Get the project root directory (assuming modules is directly under project root)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        token_path = os.path.join(project_root, 'token.pickle')
        creds_path = os.path.join(project_root, 'credentials.json')

        # The file token.pickle stores the user's access and refresh tokens
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        # if os.path.exists(token_path):
        #     creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            # with open(token_path, 'w') as token:
            #     token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)
