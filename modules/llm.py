from langchain_openai import ChatOpenAI
from langchain_aws import ChatBedrock
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from typing import List, Dict, Tuple
import boto3
from botocore.config import Config

from modules.model import EmailSummary
from modules.prompts import summarize_template, classify_template, classify_template_no_labels

class LLMProcessor:
    def __init__(self, provider: str, model_name: str):
        """Initialize LLM processor with specific provider and model"""
        
        # Initialize the appropriate LLM based on the provider
        if provider == "openai":
            self.llm = ChatOpenAI(
                temperature=0.1, 
                model=model_name
            )
        elif provider == "bedrock":
            # Configure AWS Bedrock client
            config = Config(
                region_name='us-east-2',
                retries={
                    'max_attempts': 3,
                    'mode': 'standard'
                }
            )
            
            bedrock_client = boto3.client(
                service_name='bedrock-runtime',
                region_name='us-east-2',
                config=config
            )

            self.llm = ChatBedrock(
                model_id=model_name,
                client=bedrock_client,
                model_kwargs={
                    "temperature": 0.1,
                    "max_tokens": 500,
                    "top_p": 0.1
                }
            )
        elif provider == "ollama":
            self.llm = ChatOllama(
                model=model_name,
                temperature=0.1
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        self.parser = PydanticOutputParser(pydantic_object=EmailSummary)

    def summarize_emails(self, args: any, email_info: List[Dict]) -> List[Dict]:

        prompt = ChatPromptTemplate.from_template(summarize_template)

        for email in email_info:
            messages = prompt.format_messages(
                message_content=email['content'],
                format_instructions=self.parser.get_format_instructions()
            )
            try:
                response = self.llm.invoke(messages)
                parsed_summary = self.parser.parse(response.content)
                email['summary'] = parsed_summary.model_dump()
            except Exception as e:
                print(f"Error parsing LLM response: {e}")
                email['summary'] = {
                    'summary': 'Error parsing response',
                    'category_major': 'None',
                    'category_minor': 'None',
                    'category_reasoning': 'None'
                }
        
        return email_info

    def classify_emails(self, args: any, email_info: List[Dict], available_labels: List[Dict]) -> List[Tuple[str, str]]:
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

        prompt = ChatPromptTemplate.from_template(classify_template)
        prompt_without_labels = ChatPromptTemplate.from_template(classify_template_no_labels)
        
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
            
            response = self.llm.invoke(messages)
            suggested_label = response.content.strip()
            
            # Add to our results
            classifications.append((email['subject'], suggested_label))
            
        return classifications
