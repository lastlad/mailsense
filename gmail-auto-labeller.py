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
import argparse
from pydantic import BaseModel, Field
from typing import Optional
from langchain.output_parsers import PydanticOutputParser

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

def get_unread_emails_info(args):
    """Fetches details of the unread emails."""
    service = get_gmail_service()
    
    # Get unread messages
    results = service.users().messages().list(
        userId='me',
        labelIds=['UNREAD', 'CATEGORY_UPDATES'], #'CATEGORY_PERSONAL'
        q='is:unread',
        maxResults=args.max_emails
    ).execute()
    
    messages = results.get('messages', [])
    email_info = []

    if not messages:
        print('No unread messages found.')
        return email_info

    for message in messages:
        msg = service.users().messages().get(
            userId='me',
            id=message['id'],
            #format='full'
        ).execute()

        # Extract subject from headers
        headers = msg['payload']['headers']
        subject = ''
        sender = ''
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                sender = header['value']
            if subject and sender:
                break

        # date_str = datetime.fromtimestamp(int(msg['internalDate'])/1000).strftime('%Y-%m-%d %H:%M:%S')
        # subject = f"Date: {date_str} --- Subject: {subject} --- Labels: {msg['labelIds']}"

        message_content = get_message_content(msg['payload'])
        # print(f"{message_content[:200]}..." if len(message_content) > 200 else message_content)
        # print(message_content)
        # print('----------EOM--------------')

        if message_content:
                base_file_path = f"emails/{datetime.now().strftime('%Y%m%d%H%M')}"

                # Create emails directory and any parent directories if they don't exist
                os.makedirs(base_file_path, exist_ok=True)

                # Ensure subject is safe for file paths and create subdirectories if needed
                safe_subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-', '_'))
                file_path = os.path.join(base_file_path, safe_subject + '.html')

                # Save HTML content to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(message_content)

        email_info.append({
            'sender': sender,
            'subject': subject,
            'snippet': msg['snippet'],
            'content': message_content
    })
    
    return email_info

def get_message_content(payload):
    if 'parts' in payload:
        # Multipart message
        content = []
        for part in payload['parts']:
            content.append(get_message_content(part))
        return ' '.join(content)
    elif 'body' in payload and 'data' in payload['body']:
        # Base64 encoded content
        from base64 import urlsafe_b64decode
        data = payload['body']['data']
        text = urlsafe_b64decode(data).decode('utf-8')
        return text
    return ''

def list_all_labels():
    """Fetches and prints all labels in the user's Gmail account."""
    service = get_gmail_service()
    
    try:
        results = service.users().labels().list(userId='me').execute()
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
    
class EmailSummary(BaseModel):
    summary: str = Field(description="Summary of the email content.")
    category: str = Field(description="Category of the email (e.g., Social Media, Updates, Promotions, Reminders, Receipts).")
    category_reasoning: str = Field(description="Reason for the inferred category of the email.")

def summarize_email_content(email_info):
    """
    Function to summarize the contents of the email by sending it to LLM for easier classification.
    Args:
        email_info: List of email details like Subject, Received From, Email Content etc.,
    
    Returns:
        Email summaries.
    """
    
    # Initialize the LLM
    llm = ChatOpenAI(
        temperature=0,  # We want consistent results for classification
        model="gpt-4o-mini"  # You can change this to gpt-4 if needed
    )
    
    # Create the prompt template
    template = """
        You are an expert in analyzing html content. I am providing an HTML file that contains content of an email message like articles, updates, notifications, reminders, statements etc., Please do the following:

        ###Rules for Extracting Meaningful content
        - Extract the core content from the HTML file, ignoring banners, styles, hyperlinks and other decorative or extraneous elements.
        - Do not return this information. This is only to help you with the summarization.

        ###Rules for summarizing the extracted content
        - Summarize the meaningful information in one paragraph.
        - Do not include links or any html elements in the summary.
        - Ensure that all the important points are addressed in the summary.

        ###Rules for Categorization
        - Categorize the content based on its purpose, such as Social Media Notifications, Informational Emails, Updates, Promotions, Reminders, Receipts etc..
        
        email content:
        {message_content}
        
        Provide the output in the following JSON structure:
        {format_instructions}"""
    #TODO: Update this instruction for all possible categories?
    # - Summarize the meaningful information in a structured format. Focus on key details like titles, authors, main text content, engagement metrics, and actionable links.

    prompt = ChatPromptTemplate.from_template(template)

    # Create a parser that forces the LLM to output in our desired format
    parser = PydanticOutputParser(pydantic_object=EmailSummary)
    
    for email in email_info:
        messages = prompt.format_messages(
            message_content=email['content'],
            format_instructions=parser.get_format_instructions()
            )
        # Get the classification from the LLM
        response = llm.invoke(messages)

        try:
            parsed_summary = parser.parse(response.content)
            email['summary'] = parsed_summary.model_dump()
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            email['summary'] = {
                'summary': 'Error parsing response',
                'category': 'None',
                'category_reasoning': 'None'
            }
        
    return email_info

def classify_email(email_info, available_labels):
    """
    Uses LangChain and an LLM to classify emails based on their subjects and available labels.
    
    Args:
        email_info: List of email details like Subject, Received From, Email Snippet etc.,
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
    suggest the most appropriate label for each email based on the given email subject, email content and the sender of the email. Only suggest labels from the provided list.    

    Available Labels:
    {labels}

    Email Received From:
    {email_from}

    Email Subject:
    {email_subject}

    Email Content:
    {email_content}

    Carefully read through the content of the email to understand the context of the email. Do not match to a label just because you see a related label. Let me explain with few examples:

    Example - 1:
    You may get see an email coming from discover.com domain. But the content may not be anything important or urgent and can be a promotional email. In this case the label should be `00 - Financials` and not `00 - Financials/Discover`

    Example - 2:
    The email is received from linkedin.com domain. However content may not be anything important but rather just some updates from my linkedin connections. In this case the label should not not `99 - Misc/Jobs` but `99 - Misc`

    Please respond with only the label name for this email. If no label fits, respond with "NONE".
    Choose only from the exact labels provided above."""

    template_without_labels = """You are an email classifier. Given the following email information, suggest the most appropriate label for each email based on the given email subject, email content and the sender of the email.

    Email Received From:
    {email_from}

    Email Subject:
    {email_subject}

    Email Content:
    {email_content}

    Carefully read through the content of the email to understand the context of the email. Do not match to a label just because you see a related label. Let me explain with few examples:

    Example - 1:
    You may get see an email coming from discover.com domain. But the content may not be anything important or urgent and can be a promotional email. In this case the label should be `Financials/Promotions` and not `Financials/Discover`.

    Example - 2:
    The email is received from linkedin.com domain. However content may not be anything important but rather just some updates from my linkedin connections. In this case the label should be `Misc/Updates` and not `Misc/Jobs`.

    Please respond with only the label name for this email."""

    prompt = ChatPromptTemplate.from_template(template)
    prompt_without_labels = ChatPromptTemplate.from_template(template_without_labels)
    
    classifications = []
    
    for email in email_info:
        # Create the messages for this specific email
        
        if len(label_names) > 0:
            messages = prompt.format_messages(
                labels="\n".join(label_names),
                email_from=email['sender'],
                email_subject=email['subject'],
                email_content=email['summary'] #email['snippet'] #email['content']
            )
        else:
            messages = prompt_without_labels.format_messages(
                email_from=email['sender'],
                email_subject=email['subject'],
                email_content=email['summary'] #email['snippet'] #email['content']
            )            
        
        # Get the classification from the LLM
        response = llm.invoke(messages)
        suggested_label = response.content.strip()
        
        # Add to our results
        classifications.append((email['subject'], suggested_label))
        
    return classifications


if __name__ == '__main__':
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Gmail Auto Labeller')
    parser.add_argument(
        '--llm', 
        default='gpt-4o-mini',
        required=False,
        choices=['gpt-35','gpt-4o-mini','gpt-4o','claude-sonnet-35','claude-haiku-35'],
        help='LLM provider to use.'
    )
    parser.add_argument(
        '--llm-api-keys',
        type=str,
        required=False,
        help='API Keys for the LLM provider of choice. Loads from .env if not provided.'
    )
    # parser.add_argument(
    #     '--only-unread', 
    #     type=bool, 
    #     default=True,
    #     help='Label on the unread emails. *** Be cautious as labelling all emails will be expensive.'
    # )
    parser.add_argument(
        '--use-user-labels',
        action='store_true',
        help='Use existing user defined labels to classify the email. If none of the lables match, its marked as NONE.'
    )
    parser.add_argument(
        '--create-labels', 
        type=bool, 
        default=False,
        help='Create new labels on the fly using LLM. If not, will look for a correct fit from the available labels.'
    )
    parser.add_argument(
        '--dry-run', 
        type=bool, 
        default=True,
        help='Dry run. Will not update the labels of the emails.'
    )
    parser.add_argument(
        '--max-emails', 
        type=int, 
        default=25,
        required=False,
        help='Maximum number of unread emails to process (default: 25)'
    )
    parser.add_argument(
        '--use-email-content', 
        action='store_false', 
        help='If set, will also uses the contents of the email to get additional context about the email. WARNING: Will result in additional LLM Token costs.'
    )
    parser.add_argument(
        '--print', 
        action='store_true',
        help='Print results to console in addition to saving to file'
    )
    args = parser.parse_args()

    # Get all labels first
    all_labels = []
    if args.use_user_labels:
        all_labels = list_all_labels()
    # all_labels = list_all_labels()
    
    # Get unread email info with max_results parameter
    email_info = get_unread_emails_info(args)

    # Summarize the email content for easier classification
    email_info = summarize_email_content(email_info=email_info)
    
    # Classify the emails
    print("\nClassifying emails...")
    classifications = classify_email(email_info, all_labels)
    
    # Create outputs directory if it doesn't exist
    os.makedirs('outputs', exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M')
    output_file = f'outputs/output-{timestamp}.txt'
    
    # Write results to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Summarization Results:\n")
        for email in email_info:
            f.write(f"\nEmail: {email['subject']}\n")
            f.write(f"Summary: {email['summary']}\n")
            # Print to console if --print flag is used
            if args.print:
                print(f"\nEmail: {email['subject']}")
                print(f"Summary: {email['summary']}")

        f.write("Classification Results:\n")
        for subject, label in classifications:
            f.write(f"\nEmail: {subject}\n")
            f.write(f"Suggested Label: {label}\n")
            # Print to console if --print flag is used
            if args.print:
                print(f"\nEmail: {subject}")
                print(f"Suggested Label: {label}")

    print(f"\nResults have been written to: {output_file}")