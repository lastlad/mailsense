import os
import pickle
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
import html2text

from modules.clients.base_client import EmailClient
from modules.logging import setup_logging

logger = setup_logging()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.modify'
]

class GmailClient(EmailClient):
    """Implementation of EmailClient for Gmail."""

    def __init__(self, config: Any, token_file='token.pickle', creds_file='credentials.json'):
        self.config = config
        self.token_path = self._get_abs_path(token_file)
        self.creds_path = self._get_abs_path(creds_file)
        self.service: Optional[Resource] = None
        self.text_maker = html2text.HTML2Text()
        self._configure_html2text()
        self._authenticate() # Authenticate on initialization

    def _get_abs_path(self, filename: str) -> str:
        """Gets the absolute path relative to the project root."""
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(project_root, filename)

    def _configure_html2text(self):
        """Configure HTML2Text settings."""
        self.text_maker.ignore_links = True
        self.text_maker.ignore_images = True
        self.text_maker.ignore_emphasis = False
        self.text_maker.ignore_tables = True
        self.text_maker.body_width = 0
        self.text_maker.skip_internal_links = True
        self.text_maker.inline_links = False
        self.text_maker.protect_links = False
        self.text_maker.references = False

    def _authenticate(self) -> None:
        """Handles Gmail API authentication."""
        creds = None
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
            except (EOFError, pickle.UnpicklingError) as e:
                logger.warning(f"Error loading token file {self.token_path}: {e}. Will re-authenticate.")
                creds = None # Force re-authentication
            except Exception as e:
                logger.error(f"Unexpected error loading token file {self.token_path}: {e}")
                creds = None # Force re-authentication

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired credentials.")
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}. Re-authenticating.")
                    creds = None # Force re-authentication by deleting token
                    if os.path.exists(self.token_path):
                        os.remove(self.token_path)
            
            if not creds: # Either no token, invalid token, or refresh failed
                if not os.path.exists(self.creds_path):
                    logger.error(f"Credentials file not found at {self.creds_path}. Cannot authenticate.")
                    raise FileNotFoundError(f"Credentials file not found: {self.creds_path}")
                try:
                    logger.info("No valid credentials found, starting OAuth flow.")
                    flow = InstalledAppFlow.from_client_secrets_file(self.creds_path, SCOPES)
                    # Use 0 for port to let the OS pick a free one
                    creds = flow.run_local_server(port=0, prompt='consent', authorization_prompt_message='') 
                except Exception as e:
                    logger.error(f"OAuth flow failed: {e}")
                    raise ConnectionError("Failed to authenticate via OAuth flow.") from e
            
            # Save the credentials for the next run
            try:
                with open(self.token_path, 'wb') as token:
                    pickle.dump(creds, token)
                logger.info(f"Credentials saved to {self.token_path}")
            except Exception as e:
                logger.error(f"Failed to save credentials to {self.token_path}: {e}")

        try:
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail service built successfully.")
        except Exception as e:
            logger.error(f"Failed to build Gmail service: {e}")
            self.service = None
            raise ConnectionError("Failed to build Gmail service.") from e

    # --- Implementation of EmailClient abstract methods ---

    def authenticate(self) -> Any:
        """Authenticate and return the service object."""
        if not self.service:
            self._authenticate()
        if not self.service:
             raise ConnectionError("Authentication failed, service not available.")
        return self.service

    def fetch_emails(self, args: Any) -> List[Dict]:
        """Fetches details of emails based on args (e.g., unread status, date)."""
        if not self.service:
            self.authenticate()
        
        filter_query = 'is:unread' # Default to unread

        # Handle date filtering from args object (expected attributes: date_from, date_to, days_old)
        if hasattr(args, 'date_from') and args.date_from and hasattr(args, 'date_to') and args.date_to:
            filter_query += f" after:{args.date_from} before:{args.date_to}"
        elif hasattr(args, 'days_old'): 
            date_filter = (datetime.now() - timedelta(days=args.days_old)).strftime('%Y/%m/%d')
            filter_query += f" after:{date_filter}"

        # Include specific labels if provided
        labels_to_include = ['UNREAD', 'CATEGORY_UPDATES']
        
        logger.info(f"Filter Query used: {filter_query}")
        logger.info(f"Label IDs used for filtering: {labels_to_include}")

        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=labels_to_include,
                q=filter_query,
                maxResults=args.max_emails if hasattr(args, 'max_emails') else 100 # Default max
            ).execute()
            
            messages = results.get('messages', [])
            email_info = []

            if not messages:
                logger.info('No matching messages found.')
                return email_info

            logger.info(f"Found {len(messages)} potential emails. Fetching details...")
            for message in messages:
                # Use get_message_content which now handles snippet vs full content
                content_data = self.get_message_content(
                    message['id'], 
                    fetch_full=getattr(args, 'use_full_content', False) # Check arg for full content
                )
                if content_data:
                    subject, sender, body, date_str, snippet = content_data
                    email_info.append({
                        'id': message['id'],
                        'sender': sender,
                        'subject': subject,
                        'date': date_str,
                        'content': body, # This is now either full or snippet based on fetch_full
                        'snippet': snippet # Always store snippet for potential later use
                    })
            
            logger.info(f"Successfully processed {len(email_info)} emails.")
            return email_info
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []

    def get_message_content(self, message_id: str, fetch_full: bool = False) -> Optional[Tuple[str, str, str, str, str]]:
        """
        Get the subject, sender, plain text body, date, and snippet of a specific email.
        Returns tuple (subject, sender, body, date, snippet) or None.
        Body content depends on `fetch_full`.
        """
        if not self.service:
            self.authenticate()

        try:
            msg = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full' # Get full payload to access parts if needed
            ).execute()

            payload = msg['payload']
            headers = payload.get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            date_str = datetime.fromtimestamp(int(msg['internalDate'])/1000).strftime('%Y-%m-%d %H:%M:%S')
            snippet = msg.get('snippet', '')

            body_content = snippet # Default to snippet
            if fetch_full:
                # Try to find plain text part first
                plain_text = self._find_part_by_mimetype(payload, 'text/plain')
                if plain_text:
                    body_content = self._decode_body(plain_text['body'])
                else:
                    # Fallback to HTML part if plain text not found
                    html_text = self._find_part_by_mimetype(payload, 'text/html')
                    if html_text:
                        html_content = self._decode_body(html_text['body'])
                        body_content = self.text_maker.handle(html_content)
                    else:
                        # If neither found, maybe body is directly in payload (rare for complex emails)
                        if 'body' in payload and 'data' in payload['body']:
                            body_content = self._decode_body(payload['body'])
                        else:
                            logger.warning(f"Could not extract body for message {message_id}. Using snippet.")
                            body_content = snippet # Fallback if extraction fails

            return subject, sender, body_content, date_str, snippet

        except Exception as e:
            logger.error(f"Error getting content for message {message_id}: {e}")
            return None

    def _find_part_by_mimetype(self, payload: Dict, mimetype: str) -> Optional[Dict]:
        """Recursively search parts for a specific mimetype."""
        if payload.get('mimeType') == mimetype:
            return payload
        if 'parts' in payload:
            for part in payload['parts']:
                found = self._find_part_by_mimetype(part, mimetype)
                if found:
                    return found
        return None

    def _decode_body(self, body_data: Dict) -> str:
        """Decode base64url encoded email body data."""
        data = body_data.get('data')
        if not data:
            return ''
        try:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Error decoding body data: {e}")
            return '' # Return empty string on decoding error

    def list_labels(self) -> List[Dict]:
        """Fetches user-defined labels from Gmail or falls back to config."""
        if not self.service:
            self.authenticate()
        
        try:
            results = self.service.users().labels().list(userId='me').execute()
            user_labels = [
                label for label in results.get('labels', [])
                if label.get('type') == 'user' and label.get('id') and label.get('name') # Ensure basic fields exist
            ]

            if user_labels:
                logger.info(f"Found {len(user_labels)} user-defined labels in Gmail.")
                logger.debug(f"User labels: {user_labels}")
                return user_labels
            
            # Fallback to config only if no user labels are found in Gmail
            if hasattr(self.config, 'email_labels') and self.config.email_labels:
                logger.info("No user labels found in Gmail, using default labels from config.")
                # Format them similarly to Gmail's output for consistency
                return [{'id': None, 'name': name, 'type': 'user'} for name in self.config.email_labels]
            
            logger.warning("No labels found in Gmail or config.")
            return []

        except Exception as e:
            logger.error(f"Error fetching labels: {e}")
            return []

    def apply_label(self, message_id: str, label_name: str) -> bool:
        """Applies a label to an email. Creates the label if it doesn't exist."""
        if not self.service:
            self.authenticate()

        if not label_name or label_name.strip().upper() == 'NONE':
             logger.info(f"Skipping label application for message {message_id} due to invalid label name: {label_name}")
             return False # Indicate no label was applied

        try:
            # Get current labels to find or create the desired one
            all_labels = self.list_labels() # Re-fetch or use cached if implementing caching later
            label_id = None

            # Look for existing label (case-insensitive comparison)
            for label in all_labels:
                if label['name'].lower() == label_name.lower():
                    label_id = label.get('id') # Use .get() for safety
                    if label_id: # Found an existing label with an ID
                         logger.debug(f"Found existing label '{label_name}' with ID: {label_id}")
                         break
                    else: # Label exists in config but not in Gmail yet
                         logger.info(f"Label '{label_name}' found in config but needs creation in Gmail.")
                         label_id = None # Reset to ensure creation logic runs

            # Create new label if it doesn't exist in Gmail yet
            if not label_id:
                logger.info(f"Creating new label in Gmail: {label_name}")
                label_object = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
                try:
                    created_label = self.service.users().labels().create(
                        userId='me',
                        body=label_object
                    ).execute()
                    label_id = created_label.get('id')
                    if not label_id:
                         logger.error(f"Label creation API call succeeded but returned no ID for '{label_name}'.")
                         return False
                    logger.info(f"Successfully created label '{label_name}' with ID: {label_id}")
                    # Add the newly created label to our known list for this session? Optional.
                    # self.list_labels() # Or just refetch next time needed
                except Exception as create_error:
                    logger.error(f"Error creating label '{label_name}': {create_error}")
                    return False # Failed to create the necessary label

            # Apply the label to the email
            logger.debug(f"Applying label ID '{label_id}' ({label_name}) to message {message_id}")
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            return True # Label applied successfully

        except Exception as e:
            # Catch potential errors during label lookup or application
            logger.error(f"Error applying label '{label_name}' to message {message_id}: {e}")
            return False 