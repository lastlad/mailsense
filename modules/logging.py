import logging

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("classifier.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)