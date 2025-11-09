# Google Maps Scraper

**⭐ HIGHEST VALUE ACTOR: 196K users, $8K-$15K monthly revenue potential**

Extract business listings, reviews, and location data from Google Maps.

## Features

- 🏢 Search businesses by query + location
- ⭐ Extract ratings, reviews, contact info
- 📍 GPS coordinates, addresses, opening hours
- 🔄 Bypass 120 result limit with grid splitting
- 🛡️ StealthyFetcher for anti-bot bypass
- 🌐 **Residential proxies REQUIRED**

## Installation

```bash
pip install -r ../../requirements.txt
```

## Usage

```python
from scraper import GoogleMapsScraper

scraper = GoogleMapsScraper(
    proxy_config={'enabled': True, 'proxies': [...]},
    rate_limit={'max_requests': 30, 'time_window': 60}
)

results = await scraper.run({
    "search_query": "restaurants",
    "location": "New York, NY",
    "max_results": 100,
    "include_reviews": True
})
```

## Important Notes

1. **PROXIES REQUIRED**: Google Maps WILL block direct scraping
2. **Use Residential Proxies**: Datacenter IPs get detected
3. **Rate Limiting**: Max 30 requests/minute recommended
4. **Anti-Detection**: Uses Scrapling's StealthyFetcher

## Output Schema

```json
{
  "place_id": "ChIJ...",
  "name": "Business Name",
  "category": "Restaurant",
  "address": "123 Main St, City",
  "phone": "+1 555-0123",
  "website": "https://...",
  "rating": 4.5,
  "total_reviews": 250,
  "coordinates": {"lat": 40.7128, "lng": -74.0060},
  "opening_hours": {...},
  "reviews": [...]
}
```

## Development Status

✅ **100% COMPLETE** - Full implementation ready:
- [x] Robust HTML parsing for place cards
- [x] Review extraction with JSON + HTML fallback
- [x] Multi-strategy parsing (embedded JSON + HTML)
- [x] Popular times extraction (when available)
- [x] Complete input/output validation
- [x] Proxy rotation and rate limiting
- [x] Error handling with retries

---

**Estimated Development Time**: 4-5 days
**Difficulty**: MEDIUM
**ROI**: HIGHEST (196K users)
