"""Versioned AI prompts.

Prompts are intellectual property and are versioned as code.
This allows:
- Version control and rollback
- A/B testing between versions
- Auditing which version was used
"""

from dealguard.infrastructure.ai.prompts.contract_analysis_v1 import (
    ContractAnalysisPromptV1,
)

__all__ = ["ContractAnalysisPromptV1"]
