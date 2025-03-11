import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import html2text

logger = logging.getLogger(__name__)

class EmailProcessor:
    def __init__(self, service):
        self.service = service
        self.text_maker = html2text.HTML2Text()
        self._configure_html2text()

    def _configure_html2text(self):
        """Configure HTML2Text settings for optimal conversion"""
        self.text_maker.ignore_links = True
        self.text_maker.ignore_images = True
        self.text_maker.ignore_emphasis = False
        self.text_maker.ignore_tables = True
        self.text_maker.body_width = 0
        self.text_maker.skip_internal_links = True
        self.text_maker.inline_links = False
        self.text_maker.protect_links = False
        self.text_maker.references = False

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
    
    def _process_email(self, message_id: str, use_full_content: bool = False) -> Optional[Dict]:
        msg = self.service.users().messages().get(
            userId='me',
            id=message_id
        ).execute()

        headers = msg['payload']['headers']
        subject = next((header['value'] for header in headers if header['name'] == 'Subject'), '')
        sender = next((header['value'] for header in headers if header['name'] == 'From'), '')
        date_str = datetime.fromtimestamp(int(msg['internalDate'])/1000).strftime('%Y-%m-%d %H:%M:%S')

        content = ""
        if use_full_content:
            # Only fetch and process full content if needed
            message_content = self.get_message_content(msg['payload'])
            content = self.text_maker.handle(message_content)
        else:
            # Use snippet if full content not needed
            content = msg['snippet']

        return {
            'id': message_id,
            'sender': sender,
            'subject': subject,
            'date': date_str,
            'content': content
        }

    def get_unread_emails(self, args: any) -> List[Dict]:
        """Fetches details of unread emails."""
        filter_query = 'is:unread'

        # Handle date filtering
        if args.date_from and args.date_to:
            start_date = datetime.strptime(args.date_from, '%Y-%m-%d')
            end_date = datetime.strptime(args.date_to, '%Y-%m-%d')
            date_diff = end_date - start_date
            if date_diff.days < 30:
                filter_query += f" after:{args.date_from} before:{args.date_to}"
            else:
                end_date = start_date + timedelta(days=30)
                filter_query += f" after:{args.date_from} before:{end_date.strftime('%Y-%m-%d')}"
        else: # Use days_old from config if no other date filters specified            
            date_filter = (datetime.now() - timedelta(days=args.days_old)).strftime('%Y/%m/%d')
            filter_query += f" after:{date_filter}"

        logger.info(f"Filter Query used: {filter_query}")
        
        # Get unread messages
        results = self.service.users().messages().list(
            userId='me',
            labelIds=['UNREAD', 'CATEGORY_UPDATES'],
            q=filter_query,
            maxResults=args.max_emails
        ).execute()
        
        messages = results.get('messages', [])
        email_info = []

        if not messages:
            logger.info('No unread messages found.')
            return email_info

        for message in messages:
            email_data = self._process_email(
                message['id'], 
                use_full_content=args.use_full_content
            )
            if email_data:
                email_info.append(email_data)
        
        return email_info

