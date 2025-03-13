from flask import Flask, request, jsonify
from classifier import EmailClassifier
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('classifier.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class APIArgs:
    """Simple class to mimic argparse.Namespace"""
    def __init__(self, data: Dict[str, Any]):
        self.max_emails = data.get('max_emails')
        self.days_old = data.get('days_old')
        self.date_from = data.get('date_from')
        self.date_to = data.get('date_to')
        self.use_full_content = data.get('use_full_content', False)
        self.summary_model = data.get('summary_model')
        self.classify_model = data.get('classify_model')
        self.use_user_labels = data.get('use_user_labels', False)
        self.dry_run = data.get('dry_run', True)
        self.save_steps = data.get('save_steps', False)
        self.print = data.get('print', False)

@app.route('/api/classify', methods=['POST'])
def classify_emails():
    """API endpoint to classify emails"""
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'No data provided'}), 400

        # Convert request data to args object
        args = APIArgs(request_data)
        
        # Initialize and run classifier
        classifier = EmailClassifier(args)
        classifier.run()
        
        return jsonify({
            'status': 'success',
            'message': 'Email classification completed successfully'
        })

    except Exception as e:
        logger.error(f"API Error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

def run_api():
    """Run the application in API mode"""
    app.run(host='0.0.0.0', port=50505)

if __name__ == '__main__':
    run_api() 