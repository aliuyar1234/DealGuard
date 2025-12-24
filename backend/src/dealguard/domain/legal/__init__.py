"""Legal domain - AI-Jurist feature.

This module provides:
- Legal Chat: Interactive Q&A about contracts
- Knowledge Retrieval: Search contracts using PostgreSQL FTS
- Company Profile: Organization legal context
"""

from dealguard.domain.legal.company_profile import (
    CompanyProfile,
    CompanyProfileService,
)
from dealguard.domain.legal.knowledge_retriever import (
    ClauseContext,
    ContractSearchResult,
    KnowledgeRetriever,
)

__all__ = [
    "KnowledgeRetriever",
    "ClauseContext",
    "ContractSearchResult",
    "CompanyProfile",
    "CompanyProfileService",
]
