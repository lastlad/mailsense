# MailSense

A Python application that automatically organizes Gmail using Large Language Models (LLMs). The app analyzes email content and suggests/applies appropriate labels based on the email context and existing labels.

## Features

- Automatically classify and label unread emails
- Support for multiple LLM providers (OpenAI, AWS Bedrock, Ollama)
- Use email snippets or full content for classification
- Work with predefined labels or Gmail account labels
- Dry run mode for testing
- Detailed logging and output saving
- Configurable email processing limits and date ranges
- Multiple interfaces:
  - Console application for command-line usage
  - API server for integration with other applications

## Setup

### 1. Gmail API Configuration

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API for your project
4. Create OAuth 2.0 credentials:
   - Go to Credentials → Create Credentials → OAuth Client ID
   - Application Type: Desktop Application
   - Download the client configuration file
   - Rename it to `credentials.json` and place it in the project root

### 2. Installation

1. Clone the repository:
```bash
git clone https://github.com/lastlad/mailsense.git
cd mailsense
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 3. LLM Provider Setup

The application supports three LLM providers. Configure one or more based on your needs:

#### OpenAI
1. Get your API key from [OpenAI Platform](https://platform.openai.com/)
2. Add to `.env`:
```
OPENAI_API_KEY=<your_openai_api_key>
```

#### AWS Bedrock
1. Configure AWS credentials with Bedrock access
2. Add to `.env`:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-2  # or your preferred region
```

#### Ollama
1. Install Ollama locally from [ollama.ai](https://ollama.ai)
2. Pull your desired models:
```bash
ollama pull llama-33-70B
ollama pull deepseek-r1:7b
```

## Usage

The application can be run in two modes: console interface or API server.

### Console Interface

Run the application from the command line:

```bash
python app/console.py [options]
```

#### Command Line Options

##### Core Parameters:
- `--max-emails N`: Maximum number of emails to process (default: 15)
- `--dry-run`: Run without applying labels (default: True)
- `--print`: Print results to console
- `--save-steps`: Save intermediate outputs

##### Date Filtering:
- `--days-old N`: Process emails from last N days (default: 2)
- `--date-from YYYY-MM-DD`: Process emails from this date
- `--date-to YYYY-MM-DD`: Process emails until this date

##### Content Processing:
- `--use-full-content`: Use full email content instead of snippets
- `--summary-model MODEL`: Specific model for summarization
- `--classify-model MODEL`: Specific model for classification

##### Label Management:
- `--use-user-labels`: Use Gmail account labels instead of predefined labels

By default, the application uses predefined labels from the config file. These labels are:
- Financials
- Personal
- Utilities
- Wellness
- Shopping
- Work
- Misc

To use your Gmail account's existing labels instead, add the `--use-user-labels` flag.

### API Server

Run the application as an API server:

```bash
python app/api.py
```

This starts a Flask server on port 50505 with the following endpoints:

#### Endpoints

- `GET /api/health`: Health check endpoint
- `POST /api/classify`: Classify and label emails

#### API Usage Example

To classify emails via the API:

```bash
curl -X POST http://localhost:50505/api/classify \
  -H "Content-Type: application/json" \
  -d '{
    "max_emails": 10,
    "days_old": 2,
    "use_full_content": false,
    "use_user_labels": false,
    "dry_run": true
  }'
```

### Examples

1. Quick run. Process 10 emails and dry run using predefined labels:
```bash
python app/console.py --max-emails 10 --dry-run
```

2. Basic run with defaults (using predefined labels):
```bash
python app/console.py
```

3. Process last 5 days of emails with full content:
```bash
python app/console.py --days-old 5 --use-full-content
```

4. Process emails between specific dates:
```bash
python app/console.py --date-from 2024-01-01 --date-to 2024-01-31
```

5. Process 50 emails and use Gmail account labels:
```bash
python app/console.py --max-emails 50 --use-user-labels
```

6. Test run with output:
```bash
python app/console.py --dry-run --print --save-steps
```

## Configuration

The application's default behavior can be customized in `config/config.yaml`:

- Default processing settings
- LLM provider configurations
- Available models for each provider
- Predefined email labels

## Output

The application creates the following output directories:
- `outputs/emails/`: Raw email data
- `outputs/summaries/`: Email summaries
- `outputs/classifications/`: Classification results

Logs are written to `classifier.log`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
--------------------------------

## TODO

Features:
---------
- Move emails to the label folder automatically and archive from inbox
- Label the emails identified as promotion or useless emails as Trash
    - Auto delete the emails identified as promotion or trash.

New Ideas:
- Ability to identify all the emails that have sensitive content (SSN, Passport, CCNumbers etc.,)

Code Enhancements:
------------------
- Improvise google authentication for external facing app
- Dockerize / Run as Serverless service / Chrome Extension
- Handle PII/Sensitive data parsing and skipping it to send to LLM
- Support for other email providers
