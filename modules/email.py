import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class EmailProcessor:
    def __init__(self, service):
        self.service = service

    def get_message_content(self, payload: Dict) -> str:
        if 'parts' in payload:
            # Multipart message
            content = []
            for part in payload['parts']:
                content.append(self.get_message_content(part))
            return ' '.join(content)
        elif 'body' in payload and 'data' in payload['body']:
            # Base64 encoded content
            from base64 import urlsafe_b64decode
            data = payload['body']['data']
            text = urlsafe_b64decode(data).decode('utf-8')
            return text
        return ''

    def get_unread_emails(self, args: any) -> List[Dict]:
        """Fetches details of unread emails."""

        filter_query = 'is:unread'

        if args.start_date and args.end_date:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d')
            date_diff = end_date - start_date
            if date_diff.days < 30:
                filter_query += f" after:{args.start_date} before: {args.end_date}"
            else:
                end_date = start_date + timedelta(days=30)
                filter_query += f" after:{args.start_date} before: {args.end_date}"
        elif args.days_old:
            # Calculate date from N days ago and format as YYYY/MM/DD
            date_filter = (datetime.now() - timedelta(days=args.days_old)).strftime('%Y/%m/%d')
            filter_query += f" after:{date_filter}"

        logger.info(f"Filter Query used: {filter_query}")
        
        # Get unread messages.
        results = self.service.users().messages().list(
            userId='me',
            labelIds=['UNREAD', 'CATEGORY_UPDATES'], #'CATEGORY_PERSONAL'
            q=filter_query, #'is:unread',
            maxResults=args.max_emails
        ).execute()
        
        messages = results.get('messages', [])
        email_info = []

        if not messages:
            print('No unread messages found.')
            return email_info

        for message in messages:
            email_data = self._process_email(message['id'])
            if email_data:
                email_info.append(email_data)
        
        return email_info

    def _process_email(self, message_id: str) -> Optional[Dict]:
        msg = self.service.users().messages().get(
            userId='me',
            id=message_id
            #format='full'
        ).execute()

        headers = msg['payload']['headers']
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), '')
        sender = next((header['value'] for header in headers if header['name'] == 'From'), '')
        date_str = datetime.fromtimestamp(int(msg['internalDate'])/1000).strftime('%Y-%m-%d %H:%M:%S')

        # subject = f"Date: {date_str} --- Subject: {subject} --- Labels: {msg['labelIds']}"

        message_content = self.get_message_content(msg['payload'])
        # print(f"{message_content[:200]}..." if len(message_content) > 200 else message_content)
        # print(message_content)
        # print('----------EOM--------------')
        
        if message_content:
            self._save_email_content(message_content, subject)

        return {
            'id': message_id,
            'sender': sender,
            'subject': subject,
            'date': date_str,
            'snippet': msg['snippet'],
            'content': message_content
        }

    def _save_email_content(self, content: str, subject: str):

        # Get the project root directory (assuming modules is directly under project root)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_file_path = f"{project_root}/outputs/emails/{datetime.now().strftime('%Y%m%d%H%M')}"

        # Create emails directory and any parent directories if they don't exist
        os.makedirs(base_file_path, exist_ok=True)
        
        # Ensure subject is safe for file paths and create subdirectories if needed
        safe_subject = "".join(c for c in subject if c.isalnum() or c in (' ', '-', '_'))
        file_path = os.path.join(base_file_path, safe_subject + '.html')
        
        # Save HTML content to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)