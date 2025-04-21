from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

class EmailClient(ABC):
    """Abstract base class for email client implementations."""

    @abstractmethod
    def authenticate(self) -> Any:
        """Authenticate with the email service and return a service object."""
        pass

    @abstractmethod
    def fetch_emails(self, max_results: int) -> List[Dict]:
        """Fetch a list of emails based on specified criteria."""
        pass

    @abstractmethod
    def get_message_content(self, message_id: str) -> Optional[Tuple[str, str, str]]:
        """
        Get the subject, sender, and plain text body of a specific email.
        Returns a tuple (subject, sender, body) or None if retrieval fails.
        """
        pass

    @abstractmethod
    def list_labels(self) -> List[Dict]:
        """Fetch available labels from the email service."""
        pass

    @abstractmethod
    def apply_label(self, message_id: str, label_name: str) -> bool:
        """Apply a specific label to an email. Creates the label if it doesn't exist."""
        pass