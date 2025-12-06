# External APIs for DealGuard

> This document lists all external APIs that need to be configured for full Partner-Intelligence functionality.
> **Current Status:** Mock providers are used for development. Replace with real APIs when ready.

## Required APIs for Phase 2 Partner-Intelligence

### 1. Company Data / Handelsregister APIs

#### North Data (Recommended)
- **Website:** https://www.northdata.de/
- **Purpose:** German company data, Handelsregister information, company relationships
- **Pricing:** Starts at ~€99/month for basic access
- **Features:**
  - Company search by name, HRB number, address
  - Company details (legal form, founding date, capital)
  - Management/officers information
  - Company relationships (subsidiaries, shareholders)
  - Historical data and changes
- **API Docs:** https://www.northdata.de/api
- **Environment Variables:**
  ```
  NORTHDATA_API_KEY=your-api-key
  NORTHDATA_BASE_URL=https://www.northdata.de/api/v1
  ```

#### CompanyHub (Alternative)
- **Website:** https://companyhub.de/
- **Purpose:** German business data aggregator
- **Pricing:** Contact for pricing
- **Features:**
  - Handelsregister data
  - Company financial data
  - News aggregation

#### Bundesanzeiger API
- **Website:** https://www.bundesanzeiger.de/
- **Purpose:** Official German company announcements
- **Note:** May require special agreement for API access

---

### 2. Credit Check APIs

#### Creditreform (Recommended for DACH)
- **Website:** https://www.creditreform.de/
- **Purpose:** Credit ratings, payment behavior, financial health
- **Pricing:** Enterprise pricing (contact sales)
- **Features:**
  - Credit score/rating
  - Payment index
  - Financial statements
  - Risk assessment
- **Environment Variables:**
  ```
  CREDITREFORM_API_KEY=your-api-key
  CREDITREFORM_CUSTOMER_ID=your-customer-id
  ```

#### SCHUFA B2B
- **Website:** https://www.schufa.de/b2b/
- **Purpose:** German credit bureau data
- **Pricing:** Contract-based

#### Dun & Bradstreet
- **Website:** https://www.dnb.com/
- **Purpose:** International credit data, DUNS numbers
- **Pricing:** Enterprise pricing
- **Environment Variables:**
  ```
  DNB_API_KEY=your-api-key
  DNB_SECRET=your-secret
  ```

---

### 3. Sanction Check APIs

#### opensanctions.org (Free/Open Source)
- **Website:** https://www.opensanctions.org/
- **Purpose:** Open sanctions database
- **Pricing:** Free for basic access, paid for API
- **Features:**
  - EU sanction lists
  - UN sanction lists
  - OFAC lists
  - PEP (Politically Exposed Persons) lists
- **Environment Variables:**
  ```
  OPENSANCTIONS_API_KEY=your-api-key
  ```

#### Dow Jones Risk & Compliance
- **Website:** https://www.dowjones.com/professional/risk/
- **Purpose:** Enterprise-grade sanction screening
- **Pricing:** Enterprise (very expensive)

#### ComplyAdvantage
- **Website:** https://complyadvantage.com/
- **Purpose:** AI-powered AML and sanction screening
- **Pricing:** Starts at ~$500/month

---

### 4. Insolvency Check APIs

#### Insolvenzbekanntmachungen.de
- **Website:** https://www.insolvenzbekanntmachungen.de/
- **Purpose:** Official German insolvency announcements
- **Note:** Web scraping may be required (no official API)
- **Alternative:** Use North Data which includes insolvency data

---

### 5. News Aggregation APIs

#### NewsAPI.org
- **Website:** https://newsapi.org/
- **Purpose:** News articles from various sources
- **Pricing:** Free tier available, paid from $449/month
- **Features:**
  - Search news by company name
  - Filter by date, source, language
  - German news sources included
- **Environment Variables:**
  ```
  NEWSAPI_KEY=your-api-key
  ```

#### GDELT Project (Free)
- **Website:** https://www.gdeltproject.org/
- **Purpose:** Global news monitoring
- **Pricing:** Free
- **Note:** Requires processing for sentiment analysis

---

## Implementation Priority

### Immediate (Required for MVP Testing)
1. **North Data** - Core company data
2. **opensanctions.org** - Basic sanction checking
3. **NewsAPI.org** - News monitoring

### Later (Enhanced Features)
4. **Creditreform** - Detailed credit data
5. **Dun & Bradstreet** - International coverage

---

## Configuration

### Environment Variables Template

Add these to your `.env` file when APIs are configured:

```env
# Company Data
NORTHDATA_API_KEY=
NORTHDATA_BASE_URL=https://www.northdata.de/api/v1

# Credit Check
CREDITREFORM_API_KEY=
CREDITREFORM_CUSTOMER_ID=

# Sanction Check
OPENSANCTIONS_API_KEY=

# News
NEWSAPI_KEY=

# Optional: International
DNB_API_KEY=
DNB_SECRET=
```

### Provider Configuration

In `backend/src/dealguard/config.py`, add:

```python
# External API Configuration
northdata_api_key: str | None = None
northdata_base_url: str = "https://www.northdata.de/api/v1"

creditreform_api_key: str | None = None
creditreform_customer_id: str | None = None

opensanctions_api_key: str | None = None

newsapi_key: str | None = None
```

---

## Switching from Mock to Real Providers

1. **Create real provider implementations** in `backend/src/dealguard/infrastructure/external/`:
   - `northdata_provider.py`
   - `creditreform_provider.py`
   - `opensanctions_provider.py`
   - `newsapi_provider.py`

2. **Update `PartnerCheckService`** to use real providers based on config:

```python
# In check_service.py
def get_company_provider(settings: Settings) -> CompanyDataProvider:
    if settings.northdata_api_key:
        return NorthDataProvider(settings)
    return MockCompanyProvider()  # Fallback to mock
```

3. **Test with real APIs** before going to production

---

## Cost Estimation (Monthly)

| API | Tier | Est. Cost |
|-----|------|-----------|
| North Data | Basic | €99-299 |
| Creditreform | Basic | €200-500 |
| opensanctions.org | API | €50-200 |
| NewsAPI | Business | €449 |
| **Total** | | **€800-1,450/month** |

---

## Notes

- All providers implement the interfaces defined in `backend/src/dealguard/infrastructure/external/base.py`
- Mock providers in `mock_provider.py` can be used for development/testing
- Consider caching API responses to reduce costs
- Implement rate limiting to avoid API quota issues
- DSGVO/GDPR compliance: Some data may require user consent before fetching
