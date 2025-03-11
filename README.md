# Gmail Auto Labeller

A Python application that automatically labels Gmail emails using Large Language Models (LLMs). The app analyzes email content and suggests/applies appropriate labels based on the email context and existing labels.

## Features

- Automatically classify and label unread emails
- Support for multiple LLM providers (OpenAI, AWS Bedrock, Ollama)
- Use email snippets or full content for classification
- Work with existing Gmail labels or create new ones
- Dry run mode for testing
- Detailed logging and output saving
- Configurable email processing limits and date ranges

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

### 2. LLM Provider Setup

The application supports three LLM providers. Configure one or more based on your needs:

#### OpenAI
1. Get your API key from [OpenAI Platform](https://platform.openai.com/)
2. Add to `.env`:
OPENAI_API_KEY=<your_openai_api_key>

#### AWS Bedrock
1. Configure AWS credentials with Bedrock access
2. Add to `.env`:
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-east-2  # or your preferred region

#### Ollama
1. Install Ollama locally from [Ollama.ai](https://ollama.ai)
2. Pull your desired models:
```bash
ollama pull llama-33-70B
ollama pull deepseek-r1:7b
```

### 3. Installation

1. Clone the repository:
```bash
git clone https://github.com/lastlad/gmail-auto-labeller.git
cd gmail-auto-labeller
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

## Usage

The application can be run with various command-line arguments to customize its behavior:

```bash
python app/classifier.py [options]
```

### Command Line Options

#### Core Parameters:
- `--max-emails N`: Maximum number of emails to process (default: 15)
- `--dry-run`: Run without applying labels (default: True)
- `--print`: Print results to console
- `--save-steps`: Save intermediate outputs

#### Date Filtering:
- `--days-old N`: Process emails from last N days (default: 2)
- `--date-from YYYY-MM-DD`: Process emails from this date
- `--date-to YYYY-MM-DD`: Process emails until this date

#### Content Processing:
- `--use-full-content`: Use full email content instead of snippets
- `--summary-model MODEL`: Specific model for summarization
- `--classify-model MODEL`: Specific model for classification

#### Label Management:
- `--skip-user-labels`: Skip using existing user labels
- `--create-labels`: Allow creation of new labels

### Examples

1. Basic run with defaults:
```bash
python app/classifier.py
```

2. Process last 5 days of emails with full content:
```bash
python app/classifier.py --days-old 5 --use-full-content
```

3. Process emails between specific dates:
```bash
python app/classifier.py --date-from 2024-01-01 --date-to 2024-01-31
```

4. Process 50 emails and create new labels:
```bash
python app/classifier.py --max-emails 50 --create-labels
```

5. Test run with output:
```bash
python app/classifier.py --dry-run --print --save-steps
```

## Configuration

The application's default behavior can be customized in `config/config.yaml`:

- Default processing settings
- LLM provider configurations
- Available models for each provider
- Email categories

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