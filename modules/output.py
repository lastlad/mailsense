import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class OutputWriter:
    def __init__(self, output_dir='outputs'):
        """Initialize OutputWriter with base output directory"""
        self.base_dir = Path(output_dir)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')  # Add timestamp for the run
        self.setup_directories()

    def setup_directories(self):
        """Create necessary output directories"""
        # Main directories for different processing steps
        self.dirs = {
            'emails': self.base_dir / 'emails',
            'summaries': self.base_dir / 'summaries',
            'classifications': self.base_dir / 'classifications'
        }
        
        # Create all directories
        for directory in self.dirs.values():
            directory.mkdir(parents=True, exist_ok=True)

    def save_step_output(self, 
                        data: Any, 
                        step: str, 
                        filename: Optional[str] = None,
                        print_to_console: bool = False) -> str:
        """
        Save output from a processing step
        
        Args:
            data: The data to save
            step: Processing step name ('emails', 'summaries', 'classifications')
            filename: Optional custom filename
            print_to_console: Whether to print the output to console
            
        Returns:
            Path to the saved file
        """
        if step not in self.dirs:
            raise ValueError(f"Invalid step: {step}")

        # Generate filename if not provided
        if not filename:
            filename = f"{step}_{self.timestamp}.json"  # Use run timestamp

        output_path = self.dirs[step] / filename

        try:
            # Save as JSON
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            if print_to_console:
                print(f"\n=== {step.upper()} OUTPUT ===")
                print(json.dumps(data, indent=2, ensure_ascii=False))

            logger.info(f"Saved {step} output to {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error saving {step} output: {str(e)}")
            raise