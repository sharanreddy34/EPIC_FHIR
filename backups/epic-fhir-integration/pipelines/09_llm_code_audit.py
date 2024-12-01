"""
LLM-based Code Audit Pipeline

This pipeline uses LLM (Large Language Model) capabilities to audit code changes,
identify potential issues, and generate a report for review.
"""
import os
import re
import sys
import json
import logging
import argparse
import subprocess
from typing import Dict, Any, List, Tuple, Optional

# Foundry imports (conditional based on environment)
try:
    from transforms.api import Input, Output, transform, configure
    IN_FOUNDRY = True
except ImportError:
    IN_FOUNDRY = False

# OpenAI API for code auditing
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# Import logging utility
from fhir_pipeline.utils.logging import get_logger
from fhir_pipeline.utils.retry import retry_with_backoff, RetryableError

# Configure logging
logger = get_logger(__name__, level="INFO")

# Risk level definitions
RISK_LEVEL_HIGH = "high"
RISK_LEVEL_MEDIUM = "medium"
RISK_LEVEL_LOW = "low"
RISK_LEVEL_INFO = "info"

class LLMAuditResult:
    """Represents the result of an LLM code audit."""
    
    def __init__(
        self,
        file_path: str,
        risk_level: str,
        message: str,
        line_number: Optional[int] = None,
        category: str = "general"
    ):
        """
        Initialize an LLM audit result.
        
        Args:
            file_path: Path to the file being audited
            risk_level: Risk level (high, medium, low, info)
            message: Description of the issue
            line_number: Line number where the issue was found (if applicable)
            category: Issue category (e.g., security, performance, style)
        """
        self.file_path = file_path
        self.risk_level = risk_level
        self.message = message
        self.line_number = line_number
        self.category = category
        self.timestamp = None  # Will be set when writing to output
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file_path": self.file_path,
            "risk_level": self.risk_level,
            "message": self.message,
            "line_number": self.line_number,
            "category": self.category,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMAuditResult':
        """Create from dictionary representation."""
        result = cls(
            file_path=data["file_path"],
            risk_level=data["risk_level"],
            message=data["message"],
            line_number=data.get("line_number"),
            category=data.get("category", "general")
        )
        result.timestamp = data.get("timestamp")
        return result


class CodeAuditor:
    """Responsible for auditing code using LLM technology."""
    
    def __init__(
        self,
        model_name: str = "gpt-4",
        api_key: Optional[str] = None,
        max_file_size: int = 30000,
        audit_threshold: str = RISK_LEVEL_HIGH
    ):
        """
        Initialize the code auditor.
        
        Args:
            model_name: LLM model to use (default: gpt-4)
            api_key: API key for the LLM service (if None, uses env variable)
            max_file_size: Maximum file size to audit in bytes
            audit_threshold: Minimum risk level to consider a failure
        """
        self.model_name = model_name
        self.max_file_size = max_file_size
        self.audit_threshold = audit_threshold
        
        # Configure API if OpenAI is available
        if HAS_OPENAI:
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
            if self.api_key:
                openai.api_key = self.api_key
            else:
                logger.warning("No OpenAI API key provided, code audit will be limited")
        else:
            logger.warning("OpenAI package not available, code audit will be limited")
    
    def is_available(self) -> bool:
        """Check if the LLM service is available for audits."""
        return HAS_OPENAI and self.api_key is not None
    
    def get_changed_files(self, commit_id: Optional[str] = None) -> List[str]:
        """
        Get a list of files changed in the current commit or diff.
        
        Args:
            commit_id: Optional commit ID to compare against
            
        Returns:
            List of file paths that have been changed
        """
        if commit_id:
            # Get files changed in a specific commit
            cmd = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id]
        else:
            # Get files changed and not staged/committed
            cmd = ["git", "diff", "--name-only"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            files = result.stdout.strip().split("\n")
            return [f for f in files if f]  # Filter out empty strings
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting changed files: {e}")
            return []
    
    def filter_python_files(self, files: List[str]) -> List[str]:
        """
        Filter for Python source files only.
        
        Args:
            files: List of file paths
            
        Returns:
            List of Python file paths
        """
        return [f for f in files if f.endswith(".py")]
    
    def read_file_content(self, file_path: str) -> Optional[str]:
        """
        Read the content of a file, with size restrictions.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File content or None if the file can't be read
        """
        try:
            with open(file_path, "r") as f:
                content = f.read(self.max_file_size)
                
                # Check if we truncated the file
                if f.read(1):
                    logger.warning(f"File {file_path} was truncated to {self.max_file_size} bytes")
                    content += "\n# ... FILE TRUNCATED ...\n"
                
                return content
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def mask_secrets(self, content: str) -> str:
        """
        Mask potential secrets in the code before sending to LLM.
        
        Args:
            content: Code content
            
        Returns:
            Code with secrets masked
        """
        # Patterns for common secrets
        patterns = [
            (r'(["\'](api_key|API_KEY|ApiKey|api-key)["\']\\s*[:=]\\s*["|\'])([^"\']+)(["|\'])', r'\1[MASKED_API_KEY]\4'),
            (r'(["\'](password|PASSWORD|passwd|PASSWD)["\']\\s*[:=]\\s*["|\'])([^"\']+)(["|\'])', r'\1[MASKED_PASSWORD]\4'),
            (r'(["\'](secret|SECRET|jwt|JWT)["\']\\s*[:=]\\s*["|\'])([^"\']+)(["|\'])', r'\1[MASKED_SECRET]\4'),
            (r'(["\'](access_token|ACCESS_TOKEN|token|TOKEN)["\']\\s*[:=]\\s*["|\'])([^"\']+)(["|\'])', r'\1[MASKED_TOKEN]\4')
        ]
        
        masked_content = content
        for pattern, replacement in patterns:
            masked_content = re.sub(pattern, replacement, masked_content)
        
        return masked_content
    
    @retry_with_backoff(max_retries=3, initial_delay=1.0)
    def audit_file(self, file_path: str, content: str) -> List[LLMAuditResult]:
        """
        Audit a file using LLM to identify issues.
        
        Args:
            file_path: Path to the file being audited
            content: Content of the file
            
        Returns:
            List of audit results
        """
        if not self.is_available():
            return [
                LLMAuditResult(
                    file_path=file_path,
                    risk_level=RISK_LEVEL_INFO,
                    message="Skipped LLM audit - OpenAI API not available",
                    category="system"
                )
            ]
        
        # Mask secrets before sending to LLM
        masked_content = self.mask_secrets(content)
        
        # Create the prompt for code review
        prompt = f"""
        You are a senior Python engineer conducting a comprehensive code audit.
        Review the following code for:
        
        1. Security vulnerabilities
        2. Performance issues
        3. Error handling problems
        4. API misuse
        5. Code quality issues
        6. Possible bugs or edge cases
        7. TODO comments that should be addressed
        
        Respond with a structured JSON report containing your findings.
        For each issue, include:
        - "line_number": approximate line number if identifiable, or null
        - "risk_level": one of "high", "medium", "low", or "info"
        - "category": the type of issue (security, performance, etc.)
        - "message": clear explanation of the issue and how to fix it
        
        Format your response as:
        {{
            "findings": [
                {{
                    "line_number": 42,
                    "risk_level": "high",
                    "category": "security",
                    "message": "Hardcoded API key should be moved to environment variables"
                }},
                ...
            ]
        }}
        
        Only include actual issues - if the code is good, return an empty findings list.
        High risk issues should only be flagged for serious problems like security vulnerabilities or critical bugs.
        
        Here's the code to review (path: {file_path}):
        
        ```python
        {masked_content}
        ```
        
        JSON response:
        """
        
        try:
            # Call the OpenAI API
            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Low temperature for more consistent results
                max_tokens=2000
            )
            
            # Extract JSON from response
            response_text = response.choices[0].message.content.strip()
            
            # Remove any markdown formatting if present
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            else:
                # Try to find JSON directly
                json_match = re.search(r'({.*})', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            
            try:
                result_data = json.loads(response_text)
                findings = result_data.get("findings", [])
                
                # Convert findings to LLMAuditResult objects
                audit_results = []
                for finding in findings:
                    audit_results.append(
                        LLMAuditResult(
                            file_path=file_path,
                            risk_level=finding.get("risk_level", RISK_LEVEL_INFO),
                            message=finding.get("message", "No message provided"),
                            line_number=finding.get("line_number"),
                            category=finding.get("category", "general")
                        )
                    )
                
                return audit_results
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM response as JSON: {e}")
                return [
                    LLMAuditResult(
                        file_path=file_path,
                        risk_level=RISK_LEVEL_INFO,
                        message=f"Error parsing LLM response: {e}",
                        category="system_error"
                    )
                ]
                
        except Exception as e:
            logger.error(f"Error during LLM audit: {e}")
            raise RetryableError(f"LLM API error: {str(e)}")
    
    def audit_files(self, files: List[str]) -> List[LLMAuditResult]:
        """
        Audit multiple files and collect results.
        
        Args:
            files: List of file paths to audit
            
        Returns:
            List of audit results across all files
        """
        all_results = []
        
        for file_path in files:
            logger.info(f"Auditing file: {file_path}")
            
            # Read file content
            content = self.read_file_content(file_path)
            if content is None:
                all_results.append(
                    LLMAuditResult(
                        file_path=file_path,
                        risk_level=RISK_LEVEL_INFO,
                        message="Unable to read file content",
                        category="system_error"
                    )
                )
                continue
            
            # Audit the file
            try:
                results = self.audit_file(file_path, content)
                all_results.extend(results)
                
                # Log any high-risk findings
                high_risk_count = sum(1 for r in results if r.risk_level == RISK_LEVEL_HIGH)
                if high_risk_count > 0:
                    logger.warning(f"Found {high_risk_count} high-risk issues in {file_path}")
                
            except Exception as e:
                logger.error(f"Error auditing file {file_path}: {e}")
                all_results.append(
                    LLMAuditResult(
                        file_path=file_path,
                        risk_level=RISK_LEVEL_INFO,
                        message=f"Error during audit: {str(e)}",
                        category="system_error"
                    )
                )
        
        return all_results
    
    def save_results_to_file(self, results: List[LLMAuditResult], output_path: str) -> None:
        """
        Save audit results to a file.
        
        Args:
            results: List of audit results
            output_path: Path to save the results to
        """
        # Convert results to dictionaries
        results_dicts = [result.to_dict() for result in results]
        
        # Write to file as JSON
        try:
            with open(output_path, "w") as f:
                json.dump({"results": results_dicts}, f, indent=2)
            logger.info(f"Audit results saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving audit results: {e}")
    
    def check_for_failures(self, results: List[LLMAuditResult]) -> bool:
        """
        Check if any results exceed the audit threshold.
        
        Args:
            results: List of audit results
            
        Returns:
            True if there are failures, False otherwise
        """
        # Map risk levels to numeric values for comparison
        risk_levels = {
            RISK_LEVEL_HIGH: 3,
            RISK_LEVEL_MEDIUM: 2,
            RISK_LEVEL_LOW: 1,
            RISK_LEVEL_INFO: 0
        }
        
        # Get numeric value of threshold
        threshold_value = risk_levels.get(self.audit_threshold, 0)
        
        # Check if any result has a risk level at or above the threshold
        for result in results:
            result_value = risk_levels.get(result.risk_level, 0)
            if result_value >= threshold_value:
                return True
        
        return False


# If run in Foundry
if IN_FOUNDRY:
    @configure(profile=["LLM_CODE_AUDIT"])
    @transform(
        audit_report=Output("/metrics/code_audit_results"),
    )
    def audit_code(
        spark,
        audit_report: Output,
        commit_id: Optional[str] = None
    ) -> None:
        """
        Run the LLM code audit pipeline in Foundry.
        
        Args:
            spark: SparkSession
            audit_report: Output for the audit report
            commit_id: Optional commit ID to audit
        """
        # Initialize the code auditor
        auditor = CodeAuditor(
            model_name=os.environ.get("LLM_MODEL", "gpt-4"),
            api_key=os.environ.get("OPENAI_API_KEY"),
            audit_threshold=os.environ.get("AUDIT_THRESHOLD", RISK_LEVEL_HIGH)
        )
        
        # Get changed files
        if commit_id:
            files = auditor.get_changed_files(commit_id)
        else:
            logger.warning("No commit ID provided, auditing current diff")
            files = auditor.get_changed_files()
        
        # Filter for Python files
        python_files = auditor.filter_python_files(files)
        logger.info(f"Found {len(python_files)} Python files to audit")
        
        # Audit the files
        results = auditor.audit_files(python_files)
        
        # Check for failures
        has_failures = auditor.check_for_failures(results)
        
        # Create DataFrame from results
        result_dicts = [result.to_dict() for result in results]
        df = spark.createDataFrame(result_dicts)
        
        # Write to output
        audit_report.write_dataframe(df)
        
        # Fail the transform if there are high-risk issues
        if has_failures:
            logger.error("Audit found issues exceeding threshold. See report for details.")
            raise ValueError("Code audit failed due to high-risk issues")
        
        logger.info("Code audit completed successfully")


# Command-line interface for local usage
def main():
    """Run the code audit as a command-line tool."""
    parser = argparse.ArgumentParser(description="LLM-based code audit tool")
    parser.add_argument("--commit", help="Git commit ID to audit")
    parser.add_argument("--files", help="Comma-separated list of files to audit")
    parser.add_argument("--output", default="code_audit_report.json", help="Output file path")
    parser.add_argument("--model", default="gpt-4", help="LLM model to use")
    parser.add_argument("--threshold", default=RISK_LEVEL_HIGH, help="Audit failure threshold")
    parser.add_argument("--api-key", help="OpenAI API key (or use OPENAI_API_KEY env var)")
    args = parser.parse_args()
    
    # Initialize auditor
    auditor = CodeAuditor(
        model_name=args.model,
        api_key=args.api_key,
        audit_threshold=args.threshold
    )
    
    # Determine files to audit
    if args.files:
        files = args.files.split(",")
    elif args.commit:
        files = auditor.get_changed_files(args.commit)
    else:
        files = auditor.get_changed_files()
    
    # Filter for Python files
    python_files = auditor.filter_python_files(files)
    logger.info(f"Found {len(python_files)} Python files to audit")
    
    # Audit files
    results = auditor.audit_files(python_files)
    
    # Save results
    auditor.save_results_to_file(results, args.output)
    
    # Check for failures
    has_failures = auditor.check_for_failures(results)
    
    # Print summary
    print(f"\nAudit Summary:")
    print(f"  Files audited: {len(python_files)}")
    print(f"  Total issues: {len(results)}")
    print(f"  High risk: {sum(1 for r in results if r.risk_level == RISK_LEVEL_HIGH)}")
    print(f"  Medium risk: {sum(1 for r in results if r.risk_level == RISK_LEVEL_MEDIUM)}")
    print(f"  Low risk: {sum(1 for r in results if r.risk_level == RISK_LEVEL_LOW)}")
    print(f"  Info: {sum(1 for r in results if r.risk_level == RISK_LEVEL_INFO)}")
    print(f"  Failure threshold: {args.threshold}")
    print(f"  Audit result: {'FAILED' if has_failures else 'PASSED'}")
    
    # Exit with appropriate status code
    sys.exit(1 if has_failures else 0)


if __name__ == "__main__":
    main() 