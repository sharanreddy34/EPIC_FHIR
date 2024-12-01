import os
import logging
from typing import Optional
import great_expectations as ge
from great_expectations.exceptions import DataContextError
from epic_fhir_integration.metrics.validation_metrics_recorder import ValidationMetricsRecorder

logger = logging.getLogger(__name__)

class GreatExpectationsValidator:
    def __init__(
        self,
        validation_metrics_recorder: Optional[ValidationMetricsRecorder] = None,
        context_root_dir: Optional[str] = None,
        expectation_suite_dir: Optional[str] = None
    ):
        """Initialize the Great Expectations validator.
        
        Args:
            validation_metrics_recorder: Optional validation metrics recorder
            context_root_dir: Optional root directory for Great Expectations context
            expectation_suite_dir: Optional directory containing expectation suites
        """
        self.validation_metrics_recorder = validation_metrics_recorder
        
        # If expectation_suite_dir is not provided, use the default GX directory
        if expectation_suite_dir is None:
            # Determine project root directory and use the GX expectations directory
            project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            expectation_suite_dir = os.path.join(project_dir, "great_expectations", "expectations")
            logger.info(f"Using default expectation suite directory: {expectation_suite_dir}")
        
        try:
            # Try to initialize context from standard location
            if context_root_dir:
                self.context = ge.data_context.DataContext(context_root_dir=context_root_dir)
            else:
                # Try to use the project's GX directory
                project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
                gx_dir = os.path.join(project_dir, "great_expectations")
                if os.path.exists(gx_dir):
                    self.context = ge.data_context.DataContext(context_root_dir=gx_dir)
                    logger.info(f"Using GX context from: {gx_dir}")
                else:
                    self.context = ge.data_context.DataContext()
                
            logger.info("Initialized Great Expectations context")
        except (DataContextError, IOError) as e:
            logger.warning(f"Failed to initialize Great Expectations context: {str(e)}")
            logger.warning("Using ephemeral DataContext - expectation suites will not be persisted")
            # Fallback to an in-memory context using the modern get_context helper
            self.context = ge.get_context(
                project_config=self._create_default_project_config()
            )
        
        # Load expectation suites
        self.expectation_suites = {}
        self.expectation_suite_dir = expectation_suite_dir
        
        if self.expectation_suite_dir:
            self._load_expectation_suites() 