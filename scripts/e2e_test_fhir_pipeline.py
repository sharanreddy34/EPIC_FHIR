from pathlib import Path
import os
from utils.logging import setup_debug_logging, logger
import time
import shutil
import argparse

class E2ETest:
    def __init__(self, patient_id: str, output_dir: Path, debug: bool = False, strict: bool = False, mock: bool = False):
        """
        Initialize the E2E test.
        
        Args:
            patient_id: Patient ID to test
            output_dir: Output directory
            debug: Whether to enable debug logging
            strict: Whether to run in strict mode with no mock data fallbacks
            mock: Whether to run in mock mode (no real API calls)
        """
        self.output_dir = output_dir
        self.debug = debug
        self.strict_mode = strict
        self.mock = mock
        self.patient_id = patient_id.split('@')[0]  # Remove @fhir_pipeline suffix for API calls
        self.use_spark = True  # Will be set to False if Spark is not available
        self.script_dir = Path(os.path.abspath(os.path.dirname(__file__)))
        
        # Configure logging
        setup_debug_logging(debug)
        logger.info(f"Initializing E2E test with patient ID: {self.patient_id}")
        logger.info(f"Output directory: {self.output_dir}")

    def create_dataset_structure(self, output_dir):
        """
        Create dataset structure for test outputs.
        
        Args:
            output_dir: Base output directory
            
        Returns:
            Dataset paths
        """
        logger.debug(f"Creating dataset structure in {output_dir}")
        
        # Create main directories
        start_time = time.time()
        
        # Make sure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        directories = [
            output_dir / "config",
            output_dir / "secrets",
            output_dir / "control",
            output_dir / "bronze" / "fhir_raw",
            output_dir / "silver" / "fhir_normalized",
            output_dir / "gold",
            output_dir / "metrics",
            output_dir / "monitoring"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
        
        # Copy token file to the secrets directory directly
        try:
            token_path = Path("epic_token.json")
            if token_path.exists():
                token_dest = output_dir / "secrets" / "epic_token.json"
                shutil.copy(token_path, token_dest)
                logger.info(f"Copied token file to {token_dest}")
        except Exception as e:
            logger.error(f"Error copying token file: {e}")
        
        # Create dataset configuration files
        datasets = {} 

def main():
    """Main entry point for the E2E test."""
    parser = argparse.ArgumentParser(description='Run end-to-end test for FHIR pipeline')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--output-dir', type=str, default='./e2e_test_output', help='Output directory')
    parser.add_argument('--strict', action='store_true', help='Enable strict mode (no mock data)')
    parser.add_argument('--mock', action='store_true', help='Run in mock mode (no real API calls)')
    
    args = parser.parse_args()
    
    # Configure output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create and run E2E test
    test = E2ETest(
        patient_id=TEST_PATIENT_ID,
        output_dir=output_dir, 
        debug=args.debug, 
        strict=args.strict,
        mock=args.mock
    )
    success = test.run_test()
    
    return 0 if success else 1 