### Script to automatically label the emails in gmail using LLMs.

###TODO

Features:
---------
- Labels: 
    - Pass Available labels
    - Auto Suggest new labels
    - Auto suggest new labels if no predefined labels are available
- Tag lables automatically
- Move emails to the label folder automatically and archive from inbox
- Label the emails identified as promotion or useless emails as Trash
    - Auto delete the emails identified as promotion or trash.

New Ideas:
- Ability to identify all the emails that have sensitive content (SSN, Passport, CCNumbers etc.,)

Code Enhancements:
------------------
- Add Commandline Args
- Add support for other LLMs
- Improvise google authentication for external facing app
- Dockerize / Run as Serverless service / Chrome Extension
- Handle PII/Sensitive data parsing and skipping it to send to LLM
- Support for other email providers