from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser

class EmailSummary(BaseModel):
    summary: str = Field(description="Summary of the email content.")
    category_major: str = Field(description="Major category of the email (e.g., Credit card companies, Utility companies, Social media companies etc.,).")
    category_minor: str = Field(description="Minor Category of the email (e.g., Promotions, Bills, Updates etc., ")
    category_reasoning: str = Field(description="Reason for the inferred category of the email.")
