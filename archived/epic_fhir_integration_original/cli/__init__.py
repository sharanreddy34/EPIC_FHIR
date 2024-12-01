"""
CLI entry points for the Epic FHIR Integration package.
"""

import click

from .validation_commands import validate
from .analytics_commands import analytics
from .datascience_commands import datascience

@click.group()
def cli():
    """Epic FHIR Integration CLI."""
    pass

cli.add_command(validate)
cli.add_command(analytics)
cli.add_command(datascience)

if __name__ == '__main__':
    cli() 