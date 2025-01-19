from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser

class EmailSummary(BaseModel):
    summary: str = Field(description="Summary of the email content.")
    category: str = Field(description="Category of the email (e.g., Social Media, Updates, Promotions, Reminders, Receipts).")
    category_reasoning: str = Field(description="Reason for the inferred category of the email.")
