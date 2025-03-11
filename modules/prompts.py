####################################################################################################################
## Summarize emails based on the content provided and identify some major and minor categories.
####################################################################################################################
# summarize_template = """
# You are an expert in analyzing html content. I am providing an HTML file that contains content of an email message like articles, updates, notifications, reminders, statements etc., Please do the following:

# ###Rules for Extracting Meaningful content
# - Extract the core content from the HTML file, ignoring banners, styles, hyperlinks and other decorative or extraneous elements.
# - Extract any named entity information that will help in understanding the context of the email.
# - Do not return this information. This is only to help you with the summarization.

# ###Rules for summarizing the extracted content
# - Summarize the meaningful information in one paragraph.
# - Do not include links or any html elements in the summary.
# - Ensure that all the important points are addressed in the summary including but not limited to entities, names, balances, deadlines, etc.,.

# ###Rules for Categorization
# - Categorize the content based on its purpose, such as Social Media Notifications, Informational Emails, Updates, Promotions, Reminders, Receipts etc..
# - Categorize into a Major caregory and a Minor Category. 
# - Major Category is one that identifies the entities that the content is about. Like credit card companies, utility companies, social media companies etc.,
# - Return the entity name like Chase, Discover, Cox, Linkedin, Facebook, etc., 
# - Minor Category is one that identifies the sub category like Promotions, Bills, Updates etc., 

# email content:
# {message_content}

# Provide the output in the following JSON structure:
# {format_instructions}"""

#TODO: New prompt from Reddit (https://www.reddit.com/r/LocalLLaMA/comments/1ftjbz3/shockingly_good_superintelligent_summarization/)
summarize_template = """
You are an expert in analyzing html content. I am providing an HTML file that contains content of an email message like articles, updates, notifications, reminders, statements etc., Please do the following:

###Rules for Summarization.
1.) Analyze the input text and generate 5 essential questions that, when answered, capture the main points and core meaning of the text. 
2.) When formulating your questions: 
  a. Address the central theme or argument 
  b. Identify key supporting ideas 
  c. Highlight important facts or evidence 
  d. Reveal the author's purpose or perspective 
  e. Explore any significant implications or conclusions. 
3.) Answer all of your generated questions one-by-one in detail. 

###Rules for Categorization.
- Categorize the content based on its purpose, such as Social Media Notifications, Informational Emails, Updates, Promotions, Reminders, Receipts etc..
- Categorize into a Major caregory and a Minor Category. 
- Major Category is one that identifies the entities that the content is about. Like credit card companies, utility companies, social media companies etc.,
- Return the entity name like Chase, Discover, Cox, Linkedin, Facebook, etc., 
- Minor Category is one that identifies the sub category like Promotions, Bills, Updates etc., 

email content:
{message_content}

{format_instructions}"""

####################################################################################################################
## Classify emails with labels provided.
####################################################################################################################
classify_template = """You are an email classifier. Given the following email information and available Gmail labels, 
suggest the most appropriate label for each email based on the given email subject, email content and the sender of the email. Only suggest labels from the provided list.    

Carefully read through the content of the email to understand the context of the email. Do not match to a label just because you see a related label. Let me explain with few examples:

Example - 1:
You may get see an email coming from discover.com domain. But the content may not be anything important or urgent and can be a promotional email. In this case the label should be `00 - Financials` and not `00 - Financials/Discover`

Example - 2:
The email is received from linkedin.com domain. However content may not be anything important but rather just some updates from my linkedin connections. In this case the label should not not `99 - Misc/Jobs` but `99 - Misc`

Please respond with only the label name for this email. If no label fits, respond with "NONE". Do not include any commentary.
Choose only from the given list of labels. Do not come up with new labels.

Available Labels:
{labels}

Email Received From:
{email_from}

Email Subject:
{email_subject}

Email Content:
{email_content}

"""

####################################################################################################################
## Classify emails with no labels provided.
####################################################################################################################
classify_template_no_labels = """You are an email classifier. Given the following email information, suggest the most appropriate label for each email based on the given email subject, email content and the sender of the email.

Carefully read through the content of the email to understand the context of the email. Do not match to a label just because you see a related label. Let me explain with few examples:

Example - 1:
You may get see an email coming from discover.com domain. But the content may not be anything important or urgent and can be a promotional email. In this case the label should be `Financials/Promotions` and not `Financials/Discover`.

Example - 2:
The email is received from linkedin.com domain. However content may not be anything important but rather just some updates from my linkedin connections. In this case the label should be `Misc/Updates` and not `Misc/Jobs`.

Please respond with only the label name for this email.

Email Received From:
{email_from}

Email Subject:
{email_subject}

Email Content:
{email_content}
"""