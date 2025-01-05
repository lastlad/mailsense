import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

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
        maxResults=50
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

        # date_str = datetime.fromtimestamp(int(msg['internalDate'])/1000).strftime('%Y-%m-%d %H:%M:%S')
        # subject = f"Date: {date_str} --- Subject: {subject} --- Labels: {msg['labelIds']}"
        
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
            print(f"Name: {label['name']:<30} ID: {label['id']}, Type: {label['type']}")
        
        return [label for label in labels if label['type'] == 'user']

    except Exception as e:
        print(f'An error occurred: {e}')
        return []

def classify_email(subjects, available_labels):
    """
    Uses LangChain and an LLM to classify emails based on their subjects and available labels.
    
    Args:
        subjects: List of email subject strings
        available_labels: List of Gmail label dictionaries
    
    Returns:
        List of tuples containing (subject, recommended_label)
    """
    # Extract just the label names from the label objects
    label_names = [label['name'] for label in available_labels]
    
    # Initialize the LLM
    llm = ChatOpenAI(
        temperature=0,  # We want consistent results for classification
        model="gpt-4o-mini"  # You can change this to gpt-4 if needed
    )
    
    # Create the prompt template
    template = """You are an email classifier. Given the following email information and available Gmail labels, 
    suggest the most appropriate label for each email. Only suggest labels from the provided list.

    Available Labels:
    {labels}

    Email Information:
    {email_info}

    Please respond with only the label name for this email. If no label fits, respond with "NONE".
    Choose only from the exact labels provided above."""

    prompt = ChatPromptTemplate.from_template(template)
    
    classifications = []
    
    for subject in subjects:
        # Create the messages for this specific email
        messages = prompt.format_messages(
            labels="\n".join(label_names),
            email_info=subject
        )
        
        # Get the classification from the LLM
        response = llm.invoke(messages)
        suggested_label = response.content.strip()
        
        # Add to our results
        classifications.append((subject, suggested_label))
        
    return classifications

if __name__ == '__main__':
    # Get all labels first
    all_labels = list_all_labels()
    
    # Get unread email subjects
    subjects = get_unread_subjects()
    
    # Classify the emails
    print("\nClassifying emails...")
    classifications = classify_email(subjects, all_labels)
    
    # Print results
    print("\nClassification Results:")
    for subject, label in classifications:
        print(f"\nEmail: {subject}")
        print(f"Suggested Label: {label}")