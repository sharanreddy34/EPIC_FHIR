#!/usr/bin/env python
"""
Epic FHIR Integration CLI for Palantir Foundry.

This module provides a unified command-line interface for the various FHIR
processing stages (extract, transform, quality) in Foundry.
"""

import argparse
import logging
import sys
from pathlib import Path

# Import subcommand modules
from epic_fhir_integration.cli import extract as extract_cli
from epic_fhir_integration.cli import transform_bronze as transform_bronze_cli
from epic_fhir_integration.cli import transform_gold as transform_gold_cli
from epic_fhir_integration.cli import quality as quality_cli

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def main_cli():
    """Main entry point for the unified Epic FHIR CLI."""
    parser = argparse.ArgumentParser(description="Epic FHIR Integration CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command help", required=True)

    # Extract subcommand
    parser_extract = subparsers.add_parser("extract", help="Extract FHIR resources")
    parser_extract.add_argument(
        "--resources",
        nargs="+",
        help="FHIR resource types to extract (e.g., Patient Observation)",
    )
    parser_extract.add_argument(
        "--config",
        help="Path to YAML configuration file with resource-specific parameters",
    )
    parser_extract.add_argument(
        "--output-dir",
        help="Base directory for output (alternative to --output-uri)",
    )
    parser_extract.add_argument(
        "--output-uri",
        help="Base URI for output (e.g., $DATA_ROOT/bronze)",
    )
    parser_extract.add_argument(
        "--page-limit",
        type=int,
        help="Maximum number of pages to retrieve per resource type",
    )
    parser_extract.add_argument(
        "--total-limit",
        type=int,
        help="Maximum total number of resources to retrieve per resource type",
    )
    parser_extract.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data instead of calling the API",
    )

    # Transform subcommand - handles both bronze->silver and silver->gold
    parser_transform = subparsers.add_parser("transform", help="Transform FHIR data through layers")
    parser_transform.add_argument(
        "--resources",
        nargs="+",
        help="FHIR resource types to transform (e.g., Patient Observation)",
    )
    parser_transform.add_argument(
        "--config",
        help="Path to YAML configuration file",
    )
    parser_transform.add_argument(
        "--bronze",
        help="Input Bronze data path",
    )
    parser_transform.add_argument(
        "--silver",
        help="Intermediate Silver data path (output for bronze, input for gold)",
    )
    parser_transform.add_argument(
        "--gold",
        help="Output Gold data path",
    )
    parser_transform.add_argument(
        "--validate",
        action="store_true",
        help="Validate Gold layer schemas after transformation",
    )

    # Quality subcommand
    parser_quality = subparsers.add_parser("quality", help="Run quality checks on FHIR data")
    parser_quality.add_argument(
        "--input",
        required=True,
        help="Input data path for quality checks (e.g., $DATA_ROOT/gold)",
    )
    parser_quality.add_argument(
        "--output",
        help="Output file for quality report",
    )
    parser_quality.add_argument(
        "--resource-type",
        help="Filter to specific resource type",
    )
    parser_quality.add_argument(
        "--metrics-dir",
        help="Directory to store metrics data",
    )

    args = parser.parse_args()

    # Dispatch to appropriate subcommand
    if args.command == "extract":
        # Convert args to a format expected by extract_cli.main()
        sys.argv = ["epic-fhir", "extract"]
        if args.resources:
            sys.argv.extend(["--resources"] + args.resources)
        if args.config:
            sys.argv.extend(["--config", args.config])
        if args.output_uri:
            sys.argv.extend(["--output-uri", args.output_uri])
        elif args.output_dir:
            sys.argv.extend(["--output-dir", args.output_dir])
        if args.page_limit is not None:
            sys.argv.extend(["--page-limit", str(args.page_limit)])
        if args.total_limit is not None:
            sys.argv.extend(["--total-limit", str(args.total_limit)])
        if args.mock:
            sys.argv.append("--mock")
        extract_cli.main()

    elif args.command == "transform":
        # Run bronze to silver transformation
        logger.info("Starting Bronze to Silver transformation...")
        bronze_argv = ["epic-fhir", "transform-bronze"]
        if args.resources:
            bronze_argv.extend(["--resources"] + args.resources)
        if args.config:
            bronze_argv.extend(["--config", args.config])
        if args.bronze:
            bronze_argv.extend(["--bronze-dir", args.bronze])
        if args.silver:
            bronze_argv.extend(["--silver-dir", args.silver])
        original_argv = sys.argv
        sys.argv = bronze_argv
        transform_bronze_cli.main()

        # Run silver to gold transformation
        logger.info("Starting Silver to Gold transformation...")
        gold_argv = ["epic-fhir", "transform-gold"]
        if args.resources:
            gold_argv.extend(["--resources"] + args.resources)
        if args.config:
            gold_argv.extend(["--config", args.config])
        if args.silver:
            gold_argv.extend(["--silver-dir", args.silver])
        if args.gold:
            gold_argv.extend(["--gold-dir", args.gold])
        if args.validate:
            gold_argv.append("--validate")
        sys.argv = gold_argv
        transform_gold_cli.main()
        sys.argv = original_argv
        logger.info("Transformations complete.")

    elif args.command == "quality":
        # Simplified quality assessment for Foundry
        # Run the assess_quality function if it exists in quality_cli
        if hasattr(quality_cli, 'assess_quality'):
            quality_args = argparse.Namespace(
                input_file=args.input,
                resource_type=args.resource_type,
                output=args.output,
                metrics_dir=args.metrics_dir,
                expectation_dir=None
            )
            quality_cli.assess_quality(
                quality_args.input_file,
                quality_args.resource_type,
                quality_args.output,
                quality_args.metrics_dir,
                quality_args.expectation_dir
            )
        else:
            # Fallback to simpler quality check
            logger.info(f"Running basic quality check on input: {args.input}")
            logger.info("Quality check complete. (Placeholder for full quality assessment)")


if __name__ == "__main__":
    main_cli() 