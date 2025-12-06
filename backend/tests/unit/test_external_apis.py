"""
Unit tests for External API clients.

Tests cover:
- OpenFirmenbuch provider (Austrian company data)
- OpenSanctions provider (sanctions & PEP screening)
- Fallback provider chain
- Error handling and retries
"""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from dealguard.infrastructure.external.openfirmenbuch import (
    OpenFirmenbuchProvider,
    FallbackFirmenbuchProvider,
    OPENFIRMENBUCH_BASE_URL,
)
from dealguard.infrastructure.external.opensanctions import (
    OpenSanctionsProvider,
    PEPScreeningProvider,
    OPENSANCTIONS_BASE_URL,
)
from dealguard.infrastructure.external.base import (
    CompanySearchResult,
    CompanyData,
    SanctionCheckResult,
)


class TestOpenFirmenbuchProvider:
    """Tests for OpenFirmenbuch API client."""

    @pytest.fixture
    def provider(self):
        """Create OpenFirmenbuch provider instance."""
        return OpenFirmenbuchProvider(timeout=10.0)

    @pytest.fixture
    def mock_client(self):
        """Create mock HTTP client."""
        return AsyncMock(spec=httpx.AsyncClient)

    def test_provider_name(self, provider):
        """Test provider name is correct."""
        assert provider.provider_name == "openfirmenbuch"

    def test_base_url(self, provider):
        """Test base URL is correct."""
        assert provider.base_url == OPENFIRMENBUCH_BASE_URL
        assert "openfirmenbuch.at" in provider.base_url

    @pytest.mark.asyncio
    async def test_search_companies_success(self, provider, mock_client):
        """Test successful company search."""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "companies": [
                {
                    "fn": "123456a",
                    "name": "Test GmbH",
                    "sitz": "Wien",
                    "status": "active",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        results = await provider.search_companies("Test", country="AT", limit=10)

        assert len(results) == 1
        assert results[0].name == "Test GmbH"
        assert results[0].country == "AT"
        assert results[0].handelsregister_id == "123456a"

    @pytest.mark.asyncio
    async def test_search_companies_non_at_country(self, provider):
        """Test search returns empty for non-AT countries."""
        results = await provider.search_companies("Test", country="DE", limit=10)

        assert results == []

    @pytest.mark.asyncio
    async def test_search_companies_not_found(self, provider, mock_client):
        """Test search handles 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        results = await provider.search_companies("NonexistentCompany", country="AT")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_companies_http_error(self, provider, mock_client):
        """Test search handles HTTP errors."""
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )
        provider._client = mock_client

        results = await provider.search_companies("Test", country="AT")

        assert results == []

    @pytest.mark.asyncio
    async def test_search_companies_request_error(self, provider, mock_client):
        """Test search handles request errors."""
        mock_client.get = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )
        provider._client = mock_client

        results = await provider.search_companies("Test", country="AT")

        assert results == []

    @pytest.mark.asyncio
    async def test_get_company_data_success(self, provider, mock_client):
        """Test getting company data by FN."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "fn": "123456a",
            "name": "Test GmbH",
            "sitz": "Wien",
            "stammkapital": "35.000,00 EUR",
            "geschaeftsfuehrer": ["Max Mustermann"],
            "firmenbuchgericht": "Handelsgericht Wien",
        }
        mock_response.raise_for_status = MagicMock()

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.get_company_data("123456a")

        assert result is not None
        assert result.name == "Test GmbH"
        assert result.handelsregister_id == "123456a"
        assert result.country == "AT"

    @pytest.mark.asyncio
    async def test_get_company_data_not_found(self, provider, mock_client):
        """Test get company data handles 404."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.get_company_data("999999z")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_by_fn(self, provider):
        """Test search by Firmenbuchnummer convenience method."""
        with patch.object(provider, "get_company_data") as mock_get:
            mock_get.return_value = MagicMock()

            await provider.search_by_fn("FN 123456a")

            # Should clean up FN format
            mock_get.assert_called_once_with("123456a")

    @pytest.mark.asyncio
    async def test_search_by_fn_cleans_format(self, provider):
        """Test FN format cleaning."""
        with patch.object(provider, "get_company_data") as mock_get:
            mock_get.return_value = None

            await provider.search_by_fn("FN 123 456 A")

            # Should normalize to lowercase, no spaces
            mock_get.assert_called_once_with("123456a")

    def test_extract_legal_form_gmbh(self, provider):
        """Test legal form extraction for GmbH."""
        result = provider._extract_legal_form("Test Consulting GmbH")
        assert result == "GmbH"

    def test_extract_legal_form_ag(self, provider):
        """Test legal form extraction for AG."""
        result = provider._extract_legal_form("Big Company AG")
        assert result == "AG"

    def test_extract_legal_form_kg(self, provider):
        """Test legal form extraction for KG."""
        result = provider._extract_legal_form("Partner KG")
        assert result == "KG"

    def test_extract_legal_form_gmbh_co_kg(self, provider):
        """Test legal form extraction for GmbH & Co KG."""
        result = provider._extract_legal_form("Business GmbH & Co KG")
        assert result == "GmbH & Co KG"

    def test_extract_legal_form_unknown(self, provider):
        """Test legal form extraction for unknown forms."""
        result = provider._extract_legal_form("Some Name")
        assert result is None

    def test_parse_capital_eur(self, provider):
        """Test capital parsing with EUR."""
        result = provider._parse_capital("35.000,00 EUR")
        assert result == 35000.0

    def test_parse_capital_euro_symbol(self, provider):
        """Test capital parsing with euro symbol."""
        result = provider._parse_capital("100000.00 €")
        assert result == 100000.0

    def test_parse_capital_none(self, provider):
        """Test capital parsing with None."""
        result = provider._parse_capital(None)
        assert result is None

    def test_parse_capital_invalid(self, provider):
        """Test capital parsing with invalid string."""
        result = provider._parse_capital("not a number")
        assert result is None

    @pytest.mark.asyncio
    async def test_close(self, provider):
        """Test closing the HTTP client."""
        mock_client = AsyncMock()
        provider._client = mock_client

        await provider.close()

        mock_client.aclose.assert_called_once()
        assert provider._client is None


class TestFallbackFirmenbuchProvider:
    """Tests for FallbackFirmenbuch provider chain."""

    @pytest.fixture
    def provider(self):
        """Create fallback provider instance."""
        return FallbackFirmenbuchProvider(timeout=10.0)

    def test_provider_name(self, provider):
        """Test provider name is correct."""
        assert provider.provider_name == "fallback_firmenbuch"

    @pytest.mark.asyncio
    async def test_search_tries_openfirmenbuch_first(self, provider):
        """Test that OpenFirmenbuch is tried first."""
        mock_results = [
            CompanySearchResult(
                provider_id="123a",
                name="Test GmbH",
                legal_form="GmbH",
                city="Wien",
                country="AT",
                confidence_score=1.0,
            )
        ]

        with patch.object(
            provider.openfirmenbuch, "search_companies", return_value=mock_results
        ) as mock_search:
            results = await provider.search_companies("Test", "AT", 10)

            mock_search.assert_called_once_with("Test", "AT", 10)
            assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_uses_opendata_as_fallback(self, provider):
        """Test that opendata.host is used as fallback."""
        provider.opendata_api_key = "test-key"

        with patch.object(
            provider.openfirmenbuch, "search_companies", return_value=[]
        ):
            with patch.object(
                provider, "_search_opendata_host", return_value=[]
            ) as mock_fallback:
                await provider.search_companies("Test", "AT", 10)

                mock_fallback.assert_called_once_with("Test", 10)

    @pytest.mark.asyncio
    async def test_close_closes_all_clients(self, provider):
        """Test close() closes all sub-providers."""
        with patch.object(provider.openfirmenbuch, "close") as mock_close:
            await provider.close()

            mock_close.assert_called_once()


class TestOpenSanctionsProvider:
    """Tests for OpenSanctions API client."""

    @pytest.fixture
    def provider(self):
        """Create OpenSanctions provider instance."""
        return OpenSanctionsProvider(timeout=10.0)

    @pytest.fixture
    def provider_with_key(self):
        """Create OpenSanctions provider with API key."""
        return OpenSanctionsProvider(api_key="test-api-key", timeout=10.0)

    @pytest.fixture
    def mock_client(self):
        """Create mock HTTP client."""
        return AsyncMock(spec=httpx.AsyncClient)

    def test_provider_name(self, provider):
        """Test provider name is correct."""
        assert provider.provider_name == "opensanctions"

    def test_base_url(self, provider):
        """Test base URL is correct."""
        assert provider.base_url == OPENSANCTIONS_BASE_URL
        assert "opensanctions.org" in provider.base_url

    @pytest.mark.asyncio
    async def test_check_sanctions_no_matches(self, provider, mock_client):
        """Test sanctions check with no matches."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.check_sanctions("Clean Company GmbH", country="AT")

        assert result.is_sanctioned is False
        assert result.score == 0
        assert "Keine Treffer" in result.summary

    @pytest.mark.asyncio
    async def test_check_sanctions_with_high_confidence_match(self, provider, mock_client):
        """Test sanctions check with high confidence match."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "entity-123",
                    "caption": "Sanctioned Entity",
                    "schema": "Company",
                    "score": 0.95,
                    "datasets": ["eu_fsf"],
                    "properties": {"country": ["AT"]},
                }
            ]
        }

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.check_sanctions("Sanctioned Entity", country="AT")

        assert result.is_sanctioned is True
        assert result.score > 0
        assert "WARNUNG" in result.summary

    @pytest.mark.asyncio
    async def test_check_sanctions_with_low_confidence_match(self, provider, mock_client):
        """Test sanctions check with low confidence match."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "entity-456",
                    "caption": "Similar Name",
                    "schema": "Person",
                    "score": 0.6,  # Low confidence
                    "datasets": ["us_ofac_sdn"],
                }
            ]
        }

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.check_sanctions("Similar Name", country="AT")

        # Low confidence should not be marked as sanctioned
        assert result.is_sanctioned is False
        assert "mögliche Treffer" in result.summary

    @pytest.mark.asyncio
    async def test_check_sanctions_with_aliases(self, provider, mock_client):
        """Test sanctions check with aliases."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.check_sanctions(
            "Main Name",
            country="AT",
            aliases=["Alias1", "Alias2"],
        )

        # Should have made 3 calls (main + 2 aliases)
        assert mock_client.get.call_count == 3
        assert result.raw_data["aliases_checked"] == ["Alias1", "Alias2"]

    @pytest.mark.asyncio
    async def test_check_sanctions_deduplicates_matches(self, provider, mock_client):
        """Test that duplicate matches are deduplicated."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"id": "entity-1", "caption": "Same Entity", "score": 0.9},
            ]
        }

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        # Search with alias that returns same entity
        result = await provider.check_sanctions(
            "Same Entity",
            aliases=["Same Entity Inc"],
        )

        # Should only have 1 unique match
        assert len(result.matches) == 1 if result.matches else True

    @pytest.mark.asyncio
    async def test_check_sanctions_rate_limit(self, provider, mock_client):
        """Test handling of rate limit response."""
        mock_response = MagicMock()
        mock_response.status_code = 429

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.check_sanctions("Test", country="AT")

        # Should return empty results, not fail
        assert result.is_sanctioned is False

    @pytest.mark.asyncio
    async def test_check_sanctions_http_error(self, provider, mock_client):
        """Test handling of HTTP errors."""
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )
        provider._client = mock_client

        result = await provider.check_sanctions("Test", country="AT")

        assert result.is_sanctioned is False
        assert "fehlgeschlagen" in result.summary

    @pytest.mark.asyncio
    async def test_check_entity(self, provider, mock_client):
        """Test getting entity details."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "entity-123",
            "caption": "Entity Name",
            "schema": "Person",
        }

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.check_entity("entity-123")

        assert result is not None
        assert result["id"] == "entity-123"

    @pytest.mark.asyncio
    async def test_check_entity_not_found(self, provider, mock_client):
        """Test entity not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.check_entity("nonexistent")

        assert result is None

    def test_is_high_confidence_match_true(self, provider):
        """Test high confidence match detection."""
        match = {"score": 0.9}
        assert provider._is_high_confidence_match(match) is True

    def test_is_high_confidence_match_false(self, provider):
        """Test low confidence match detection."""
        match = {"score": 0.6}
        assert provider._is_high_confidence_match(match) is False

    def test_is_high_confidence_match_threshold(self, provider):
        """Test threshold for high confidence (0.8)."""
        assert provider._is_high_confidence_match({"score": 0.8}) is True
        assert provider._is_high_confidence_match({"score": 0.79}) is False

    def test_format_matches(self, provider):
        """Test match formatting."""
        matches = [
            {
                "id": "entity-1",
                "caption": "Test Entity",
                "schema": "Company",
                "score": 0.95,
                "datasets": ["eu_fsf"],
                "properties": {
                    "country": ["AT", "DE"],
                    "topics": ["sanction"],
                },
            }
        ]

        formatted = provider._format_matches(matches)

        assert len(formatted) == 1
        assert formatted[0]["id"] == "entity-1"
        assert formatted[0]["name"] == "Test Entity"
        assert formatted[0]["score"] == 0.95
        assert "AT" in formatted[0]["countries"]

    def test_format_matches_limits_to_10(self, provider):
        """Test that only 10 matches are returned."""
        matches = [{"id": f"entity-{i}", "score": 0.9} for i in range(20)]

        formatted = provider._format_matches(matches)

        assert len(formatted) == 10

    def test_error_result(self, provider):
        """Test error result creation."""
        result = provider._error_result("Test error message")

        assert result.is_sanctioned is False
        assert result.score == 0
        assert "fehlgeschlagen" in result.summary
        assert result.raw_data["error"] == "Test error message"

    @pytest.mark.asyncio
    async def test_close(self, provider):
        """Test closing the HTTP client."""
        mock_client = AsyncMock()
        provider._client = mock_client

        await provider.close()

        mock_client.aclose.assert_called_once()
        assert provider._client is None


class TestPEPScreeningProvider:
    """Tests for PEP (Politically Exposed Persons) screening."""

    @pytest.fixture
    def provider(self):
        """Create PEP screening provider."""
        return PEPScreeningProvider(timeout=10.0)

    def test_provider_name(self, provider):
        """Test provider name is correct."""
        assert provider.provider_name == "opensanctions_pep"

    @pytest.mark.asyncio
    async def test_check_pep_no_match(self, provider):
        """Test PEP check with no match."""
        with patch.object(
            provider._sanctions,
            "check_sanctions",
            return_value=SanctionCheckResult(
                is_sanctioned=False,
                matches=None,
                lists_checked=[],
                score=0,
                summary="No matches",
            ),
        ):
            result = await provider.check_pep("John Doe", country="AT")

            assert result["is_pep"] is False
            assert "Nein" in result["summary"]

    @pytest.mark.asyncio
    async def test_check_pep_with_pep_match(self, provider):
        """Test PEP check with PEP match."""
        with patch.object(
            provider._sanctions,
            "check_sanctions",
            return_value=SanctionCheckResult(
                is_sanctioned=False,
                matches=[
                    {
                        "id": "person-1",
                        "name": "Politician Name",
                        "score": 0.9,
                        "topics": ["pep", "role.head_of_state"],
                    }
                ],
                lists_checked=[],
                score=50,
                summary="Matches found",
            ),
        ):
            result = await provider.check_pep("Politician Name", country="AT")

            assert result["is_pep"] is True
            assert "Ja" in result["summary"]
            assert len(result["matches"]) == 1

    @pytest.mark.asyncio
    async def test_check_pep_filters_non_pep_matches(self, provider):
        """Test that non-PEP matches are filtered out."""
        with patch.object(
            provider._sanctions,
            "check_sanctions",
            return_value=SanctionCheckResult(
                is_sanctioned=False,
                matches=[
                    {
                        "id": "company-1",
                        "name": "Sanctioned Company",
                        "score": 0.9,
                        "topics": ["sanction"],  # Not PEP
                    },
                    {
                        "id": "person-1",
                        "name": "PEP Person",
                        "score": 0.85,
                        "topics": ["politician"],  # Is PEP
                    },
                ],
                lists_checked=[],
                score=50,
                summary="Matches found",
            ),
        ):
            result = await provider.check_pep("Test Name", country="AT")

            # Should only include PEP matches
            assert len(result["matches"]) == 1
            assert result["matches"][0]["id"] == "person-1"

    @pytest.mark.asyncio
    async def test_check_pep_low_confidence_not_flagged(self, provider):
        """Test that low confidence PEP matches don't flag as PEP."""
        with patch.object(
            provider._sanctions,
            "check_sanctions",
            return_value=SanctionCheckResult(
                is_sanctioned=False,
                matches=[
                    {
                        "id": "person-1",
                        "name": "Similar Name",
                        "score": 0.5,  # Low confidence
                        "topics": ["pep"],
                    }
                ],
                lists_checked=[],
                score=25,
                summary="Possible matches",
            ),
        ):
            result = await provider.check_pep("Different Name", country="AT")

            assert result["is_pep"] is False

    @pytest.mark.asyncio
    async def test_check_pep_handles_error(self, provider):
        """Test PEP check handles errors gracefully."""
        with patch.object(
            provider._sanctions,
            "check_sanctions",
            side_effect=Exception("API error"),
        ):
            result = await provider.check_pep("Test Name", country="AT")

            assert result["is_pep"] is False
            assert "error" in result
            assert "fehlgeschlagen" in result["summary"]

    @pytest.mark.asyncio
    async def test_close(self, provider):
        """Test closing the provider."""
        with patch.object(provider._sanctions, "close") as mock_close:
            await provider.close()

            mock_close.assert_called_once()


class TestAPIAuthentication:
    """Tests for API authentication handling."""

    @pytest.mark.asyncio
    async def test_opensanctions_api_key_in_header(self):
        """Test that API key is included in request headers."""
        provider = OpenSanctionsProvider(api_key="test-api-key")

        # Get client to trigger header setup
        client = await provider._get_client()

        assert "Authorization" in client.headers
        assert "ApiKey test-api-key" in client.headers["Authorization"]

        await provider.close()

    @pytest.mark.asyncio
    async def test_opensanctions_no_api_key(self):
        """Test client without API key."""
        provider = OpenSanctionsProvider()

        client = await provider._get_client()

        assert "Authorization" not in client.headers

        await provider.close()


class TestListsChecked:
    """Tests for sanction lists metadata."""

    @pytest.fixture
    def provider(self):
        return OpenSanctionsProvider()

    @pytest.mark.asyncio
    async def test_lists_checked_included_in_response(self, provider):
        """Test that checked lists are included in response."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.check_sanctions("Test Company", country="AT")

        assert len(result.lists_checked) > 0
        assert "EU Sanctions (CFSP)" in result.lists_checked
        assert "UN Consolidated Sanctions" in result.lists_checked
        assert "US OFAC SDN" in result.lists_checked

        await provider.close()
