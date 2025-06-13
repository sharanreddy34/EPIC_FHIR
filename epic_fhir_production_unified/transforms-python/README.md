# Epic FHIR Integration for Foundry

This module provides a production-ready pipeline for extracting, transforming, and analyzing FHIR data from Epic's API in Palantir Foundry.

## Migration Complete

✅ Successful migration of source code:
- Legacy code has been moved to `legacy_src/` with a backup in `backups/`
- Production code is now in `transforms-python/src/epic_fhir_integration/`
- Added clear documentation in the project README

✅ Fixed code issues:
- Added missing `import time` in `utils/logging.py`
- Made all code Foundry-compatible with proper imports
- Created test stubs for local development

✅ Enhanced FHIR patient extraction for LLM:
- Added robust patient narrative generation in `llm/patient_narrative.py`
- Implemented comprehensive data extraction with `_revinclude` parameters
- Specialized processing for echocardiography/ultrasound reports
- Created robust test cases

## Deployment Checklist

Before deploying to Foundry:

1. Ensure all secrets are set in the `epic-fhir-api` secret scope:
   - `EPIC_CLIENT_ID`
   - `EPIC_PRIVATE_KEY`
   - `EPIC_BASE_URL`

2. Run tests in the Foundry environment where `transforms.api` is available

3. Monitor initial extractions closely, especially for error rates and performance metrics

4. Review the generated patient narratives to ensure they capture all necessary clinical context

## Known Limitations

When testing locally:
- Some tests require the Foundry `transforms.api` module which is only available in Foundry
- For pure logic testing, use functions that don't depend on Foundry infrastructure
- Use the Foundry SDK or mock the dependencies as shown in our test stubs 