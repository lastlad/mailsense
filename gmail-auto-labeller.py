import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Gets Gmail API service instance."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def get_unread_subjects():
    """Fetches subjects of unread emails."""
    service = get_gmail_service()
    
    # Get unread messages
    results = service.users().messages().list(
        userId='me',
        labelIds=['UNREAD', 'CATEGORY_UPDATES'],
        q='is:unread',
        maxResults=10
    ).execute()
    
    messages = results.get('messages', [])
    subjects = []

    if not messages:
        print('No unread messages found.')
        return subjects

    for message in messages:
        msg = service.users().messages().get(
            userId='me',
            id=message['id']
        ).execute()
        
        # Extract subject from headers
        headers = msg['payload']['headers']
        subject = ''
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
                break

        subject = f"{subject} --- Labels: {msg['labelIds']}"
        
        subjects.append(subject)
    
    return subjects

def list_all_labels():
    """Fetches and prints all labels in the user's Gmail account."""
    service = get_gmail_service()
    
    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        if not labels:
            print('No labels found.')
            return []

        print('Labels:')
        for label in labels:
            print(f"Name: {label['name']:<30} ID: {label['id']}")
        
        return labels

    except Exception as e:
        print(f'An error occurred: {e}')
        return []

if __name__ == '__main__':
    list_all_labels()

    subjects = get_unread_subjects()
    print("\nUnread email subjects:")
    for subject in subjects:
        print(f"- {subject}")
