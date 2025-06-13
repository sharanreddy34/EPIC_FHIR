import argparse
from pathlib import Path
from log import setup_debug_logging, enable_strict_mode, logger

def main():
    """Main entry point for the local pipeline."""
    parser = argparse.ArgumentParser(description="Run FHIR pipeline locally")
    parser.add_argument("--patient-id", required=True, help="Patient ID for extraction")
    parser.add_argument("--output-dir", default="./local_output", help="Output directory")
    parser.add_argument("--steps", default="extract,transform,gold", help="Pipeline steps to run")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--strict", action="store_true", help="Enable strict mode (no mock data)")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (generate mock data)")
    
    args = parser.parse_args()
    
    # Configure logging
    setup_debug_logging(args.debug)
    
    # Enable strict mode if requested
    if args.strict:
        enable_strict_mode()
        logger.info("STRICT MODE ENABLED - No mock data will be used")
        
        if args.mock:
            logger.error("Cannot use both --strict and --mock flags")
            return 1
    
    # Create datasets and directory structure
    output_dir = Path(args.output_dir)
    
    # ... existing code ... 