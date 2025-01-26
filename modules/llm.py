from langchain_openai import ChatOpenAI
from langchain_aws import ChatBedrock
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from typing import List, Dict, Tuple

from modules.model import EmailSummary

class LLMProcessor:
    def __init__(self, args: any):
       
        # Initialize the appropriate LLM based on the provider
        if args.provider == "openai":
            self.llm = ChatOpenAI(temperature=0.3, model=args.model_name)
        elif args.provider == "bedrock":
            self.llm = ChatBedrock(
                model_id=args.model_name,
                model_kwargs={"temperature": 0.3}
            )
        elif args.provider == "ollama":
            self.llm = ChatOllama(
                model=args.model_name,
                temperature=0.3
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {args.provider}")

        self.parser = PydanticOutputParser(pydantic_object=EmailSummary)

    def summarize_emails(self, args: any, email_info: List[Dict]) -> List[Dict]:

        template = """
            You are an expert in analyzing html content. I am providing an HTML file that contains content of an email message like articles, updates, notifications, reminders, statements etc., Please do the following:

            ###Rules for Extracting Meaningful content
            - Extract the core content from the HTML file, ignoring banners, styles, hyperlinks and other decorative or extraneous elements.
            - Extract any named entity information that will help in understanding the context of the email.
            - Do not return this information. This is only to help you with the summarization.

            ###Rules for summarizing the extracted content
            - Summarize the meaningful information in one paragraph.
            - Do not include links or any html elements in the summary.
            - Ensure that all the important points are addressed in the summary including but not limited to entities, names, balances, deadlines, etc.,.

            ###Rules for Categorization
            - Categorize the content based on its purpose, such as Social Media Notifications, Informational Emails, Updates, Promotions, Reminders, Receipts etc..
            - Categorize into a Major caregory and a Minor Category. 
            - Major Category is one that identifies the entities that the content is about. Like credit card companies, utility companies, social media companies etc.,
            - Return the entity name like Chase, Discover, Cox, Linkedin, Facebook, etc., 
            - Minor Category is one that identifies the sub category like Promotions, Bills, Updates etc., 
            
            email content:
            {message_content}
            
            Provide the output in the following JSON structure:
            {format_instructions}"""

        prompt = ChatPromptTemplate.from_template(template)

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
