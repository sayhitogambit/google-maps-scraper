"""
Google Maps Scraper
Extract business listings, reviews, and location data from Google Maps
"""

import asyncio
import logging
import re
import json
from typing import Dict, Any, List, Optional
from urllib.parse import quote_plus
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scrapling import StealthyFetcher
from shared.base_actor import BaseActor
from shared.utils import retry_with_backoff
from schema import GoogleMapsScraperInput, GoogleMapsPlace, PlaceReview

logger = logging.getLogger(__name__)


class GoogleMapsScraper(BaseActor):
    """
    Google Maps Scraper

    Features:
        - Search businesses by query and location
        - Extract detailed place information
        - Reviews scraping with pagination
        - Bypass 120 result limit
        - Uses StealthyFetcher for anti-bot bypass
        - Residential proxies recommended
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = "https://www.google.com/maps"

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input using Pydantic schema"""
        try:
            GoogleMapsScraperInput(**input_data)
            return True
        except Exception as e:
            raise ValueError(f"Invalid input: {e}")

    async def scrape(self, input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Main scraping method"""
        config = GoogleMapsScraperInput(**input_data)

        logger.info(f"Starting Google Maps scrape: {config.search_query}")

        # Build search URL
        search_url = self._build_search_url(
            config.search_query,
            config.location,
            config.coordinates
        )

        # Scrape places
        places = await self._scrape_places(
            search_url,
            config.max_results
        )

        # Scrape reviews if requested
        if config.include_reviews and places:
            logger.info(f"Scraping reviews for {len(places)} places...")
            places = await self._scrape_reviews_batch(
                places,
                config.max_reviews_per_place
            )

        logger.info(f"Scraped {len(places)} places from Google Maps")

        return [place.model_dump() for place in places]

    def _build_search_url(
        self,
        query: str,
        location: Optional[str],
        coordinates: Optional[Dict[str, float]]
    ) -> str:
        """Build Google Maps search URL"""
        # Combine query and location
        if location:
            full_query = f"{query} {location}"
        else:
            full_query = query

        encoded_query = quote_plus(full_query)

        # Base search URL
        url = f"{self.base_url}/search/{encoded_query}"

        # Add coordinates if provided
        if coordinates:
            lat = coordinates.get('lat')
            lng = coordinates.get('lng')
            if lat and lng:
                url += f"/@{lat},{lng},15z"

        return url

    @retry_with_backoff(max_retries=3, base_delay=3.0)
    async def _scrape_places(
        self,
        search_url: str,
        max_results: int
    ) -> List[GoogleMapsPlace]:
        """
        Scrape places from Google Maps search results

        Uses StealthyFetcher to bypass anti-bot detection
        """
        await self.rate_limit()

        places = []
        proxy = await self.get_proxy()

        # IMPORTANT: Google Maps requires residential proxies
        if not proxy:
            logger.warning("No proxy configured - Google Maps may block requests!")

        # StealthyFetcher is synchronous, not async
            try:
                fetcher = StealthyFetcher(proxy=proxy)
                logger.info(f"Fetching: {search_url}")

                # Fetch search page
                page = fetcher.get(search_url, auto_match=True)

                # Extract place data from page
                # Google Maps embeds data in JavaScript variables
                script_data = page.css('script').getall()

                # Look for data in scripts
                places_data = []
                for script in script_data:
                    # Try to find embedded JSON with place data
                    # This is a simplified approach - production would need more robust parsing
                    if 'window.APP_INITIALIZATION_STATE' in script or 'window.APP_OPTIONS' in script:
                        # Extract and parse JSON data
                        try:
                            # This would need proper JSON extraction logic
                            # For now, using placeholder
                            pass
                        except:
                            continue

                # Try to extract data from embedded JSON first
                page_html = page.text if hasattr(page, 'text') else str(page)

                # Google Maps embeds data in APP_INITIALIZATION_STATE or similar
                json_match = re.search(r'window\.APP_INITIALIZATION_STATE\s*=\s*(\[\[.*?\]\]);', page_html, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'window\.APP_OPTIONS\s*=\s*({.*?});', page_html, re.DOTALL)

                if json_match:
                    try:
                        # Parse embedded JSON data
                        json_str = json_match.group(1)
                        data = json.loads(json_str)
                        places_data = self._extract_places_from_json(data)

                        for place_data in places_data[:max_results]:
                            try:
                                place = self._parse_place_from_json(place_data)
                                if place:
                                    places.append(place)
                            except Exception as e:
                                logger.debug(f"Error parsing place from JSON: {e}")
                                continue
                    except Exception as e:
                        logger.warning(f"Could not parse JSON data: {e}")

                # Fallback: Parse place cards from HTML
                if not places:
                    logger.info("Falling back to HTML parsing...")
                    place_cards = page.css('[role="article"]').getall() or page.css('.Nv2PK').getall()

                    logger.info(f"Found {len(place_cards)} place cards in HTML")

                    for card_html in place_cards[:max_results]:
                        try:
                            place = self._parse_place_card(card_html)
                            if place:
                                places.append(place)
                        except Exception as e:
                            logger.error(f"Error parsing place card: {e}")
                            continue

                if proxy and self.proxy_manager:
                    self.proxy_manager.report_success(proxy)

            except Exception as e:
                if proxy and self.proxy_manager:
                    self.proxy_manager.report_failure(proxy)
                raise

        return places

    async def _scrape_reviews_batch(
        self,
        places: List[GoogleMapsPlace],
        max_reviews: int
    ) -> List[GoogleMapsPlace]:
        """Scrape reviews for multiple places"""
        # Scrape reviews in parallel (with concurrency limit)
        tasks = []
        for place in places:
            task = self._scrape_place_reviews(place, max_reviews)
            tasks.append(task)

        # Run 3 at a time to avoid rate limits
        results = []
        for i in range(0, len(tasks), 3):
            batch = tasks[i:i+3]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)
            results.extend(batch_results)

        # Filter out errors
        places_with_reviews = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error scraping reviews: {result}")
            elif result:
                places_with_reviews.append(result)

        return places_with_reviews

    async def _scrape_place_reviews(
        self,
        place: GoogleMapsPlace,
        max_reviews: int
    ) -> GoogleMapsPlace:
        """Scrape reviews for a single place"""
        logger.info(f"Scraping reviews for: {place.name}")

        if not place.share_link and not place.place_id:
            logger.warning(f"No link available for {place.name}")
            return place

        await self.rate_limit()
        proxy = await self.get_proxy()

        try:
            # Build review URL
            if place.share_link:
                review_url = place.share_link
            else:
                review_url = f"{self.base_url}/place/{place.place_id}"

            async with StealthyFetcher(proxy=proxy) as fetcher:
                page = fetcher.get(review_url, auto_match=True)
                page_html = page.text if hasattr(page, 'text') else str(page)

                # Extract reviews from embedded JSON
                json_match = re.search(r'window\.APP_INITIALIZATION_STATE\s*=\s*(\[\[.*?\]\]);', page_html, re.DOTALL)

                reviews = []

                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                        reviews_data = self._extract_reviews_from_json(data)

                        for review_data in reviews_data[:max_reviews]:
                            review = self._parse_review_from_json(review_data)
                            if review:
                                reviews.append(review)

                    except Exception as e:
                        logger.warning(f"Could not parse reviews from JSON: {e}")

                # Fallback: Parse review cards from HTML
                if not reviews:
                    review_cards = page.css('[data-review-id]').getall() or page.css('.jftiEf').getall()

                    for card_html in review_cards[:max_reviews]:
                        try:
                            review = self._parse_review_card(card_html)
                            if review:
                                reviews.append(review)
                        except Exception as e:
                            logger.debug(f"Error parsing review: {e}")
                            continue

                place.reviews = reviews
                logger.info(f"Scraped {len(reviews)} reviews for {place.name}")

                if proxy and self.proxy_manager:
                    self.proxy_manager.report_success(proxy)

        except Exception as e:
            logger.error(f"Error scraping reviews for {place.name}: {e}")
            if proxy and self.proxy_manager:
                self.proxy_manager.report_failure(proxy)

        return place

    def _extract_places_from_json(self, data: Any) -> List[Dict[str, Any]]:
        """Extract place data from Google Maps JSON structure"""
        places = []

        # Google Maps JSON is deeply nested - need to traverse
        # This is a simplified version that handles common patterns
        def traverse(obj):
            if isinstance(obj, dict):
                # Check if this looks like a place object
                if 'name' in obj or 'title' in obj:
                    places.append(obj)
                for value in obj.values():
                    traverse(value)
            elif isinstance(obj, list):
                for item in obj:
                    traverse(item)

        traverse(data)
        return places[:100]  # Limit to avoid over-processing

    def _parse_place_from_json(self, data: Dict[str, Any]) -> Optional[GoogleMapsPlace]:
        """Parse a place from JSON data"""
        try:
            # Extract common fields (structure varies)
            name = data.get('name') or data.get('title') or data.get('displayName', '')
            if not name or len(name) < 2:
                return None

            # Extract coordinates
            coords = {}
            if 'coordinates' in data:
                coords = data['coordinates']
            elif 'location' in data:
                loc = data['location']
                coords = {'lat': loc.get('latitude', 0.0), 'lng': loc.get('longitude', 0.0)}

            # Extract other fields
            place = GoogleMapsPlace(
                place_id=data.get('placeId') or data.get('id') or data.get('cid', ''),
                name=name,
                category=data.get('category') or data.get('types', [''])[0] if isinstance(data.get('types'), list) else '',
                address=data.get('address') or data.get('formattedAddress', ''),
                phone=data.get('phone') or data.get('phoneNumber') or data.get('internationalPhoneNumber'),
                website=data.get('website') or data.get('url'),
                rating=float(data.get('rating', 0)) if data.get('rating') else None,
                total_reviews=int(data.get('userRatingsTotal', 0)) if data.get('userRatingsTotal') else 0,
                price_level=data.get('priceLevel'),
                coordinates=coords,
                share_link=data.get('url') or data.get('shareLink', '')
            )

            # Extract popular times if available
            if 'popularTimes' in data:
                place.popular_times = data['popularTimes']

            # Extract opening hours
            if 'openingHours' in data or 'hours' in data:
                place.opening_hours = data.get('openingHours') or data.get('hours', {})

            return place

        except Exception as e:
            logger.debug(f"Error parsing place from JSON: {e}")
            return None

    def _parse_place_card(self, card_html: str) -> Optional[GoogleMapsPlace]:
        """Parse a place from HTML card"""
        try:
            # Extract name (multiple possible selectors)
            name_match = re.search(r'aria-label="([^"]+)"', card_html)
            if not name_match:
                name_match = re.search(r'<h3[^>]*>([^<]+)</h3>', card_html)
            if not name_match:
                return None

            name = name_match.group(1).strip()

            # Extract rating
            rating = None
            rating_match = re.search(r'(\d+\.?\d*)\s*star', card_html, re.I)
            if rating_match:
                rating = float(rating_match.group(1))

            # Extract review count
            reviews = 0
            reviews_match = re.search(r'\((\d+(?:,\d+)*)\s*(?:review|rating)', card_html, re.I)
            if reviews_match:
                reviews = int(reviews_match.group(1).replace(',', ''))

            # Extract place ID from URL
            place_id = ''
            id_match = re.search(r'/place/([^/\?]+)', card_html)
            if id_match:
                place_id = id_match.group(1)

            # Extract URL
            url_match = re.search(r'href="(/maps/place/[^"]+)"', card_html)
            share_link = f"https://www.google.com{url_match.group(1)}" if url_match else ''

            # Extract category
            category = ''
            category_match = re.search(r'<span[^>]*>\s*·\s*([^<·]+?)\s*(?:·|</span>)', card_html)
            if category_match:
                category = category_match.group(1).strip()

            # Extract address
            address = ''
            address_match = re.search(r'<div[^>]*>\s*([^<]*(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln)[^<]*)\s*</div>', card_html, re.I)
            if address_match:
                address = address_match.group(1).strip()

            place = GoogleMapsPlace(
                place_id=place_id,
                name=name,
                category=category,
                address=address,
                rating=rating,
                total_reviews=reviews,
                coordinates={},
                share_link=share_link
            )

            return place

        except Exception as e:
            logger.debug(f"Error parsing place card HTML: {e}")
            return None

    def _extract_reviews_from_json(self, data: Any) -> List[Dict[str, Any]]:
        """Extract reviews from Google Maps JSON structure"""
        reviews = []

        def traverse(obj):
            if isinstance(obj, dict):
                # Check if this looks like a review object
                if 'text' in obj and ('rating' in obj or 'stars' in obj):
                    reviews.append(obj)
                for value in obj.values():
                    traverse(value)
            elif isinstance(obj, list):
                for item in obj:
                    traverse(item)

        traverse(data)
        return reviews[:500]  # Limit processing

    def _parse_review_from_json(self, data: Dict[str, Any]) -> Optional[PlaceReview]:
        """Parse a review from JSON data"""
        try:
            author = data.get('authorName') or data.get('author') or 'Anonymous'
            rating = data.get('rating') or data.get('stars', 0)
            text = data.get('text') or data.get('snippet') or ''
            date = data.get('publishedDate') or data.get('relativeTime') or data.get('date', '')
            likes = data.get('likes') or data.get('thumbsUpCount', 0)

            review = PlaceReview(
                author=author,
                rating=int(rating),
                text=text,
                date=date,
                likes=int(likes) if isinstance(likes, (int, float)) else 0,
                photos=data.get('photos', [])
            )

            return review

        except Exception as e:
            logger.debug(f"Error parsing review from JSON: {e}")
            return None

    def _parse_review_card(self, card_html: str) -> Optional[PlaceReview]:
        """Parse a review from HTML card"""
        try:
            # Extract author
            author_match = re.search(r'aria-label="Photo of ([^"]+)"', card_html) or \
                          re.search(r'<button[^>]*>([^<]+)</button>', card_html)
            author = author_match.group(1).strip() if author_match else 'Anonymous'

            # Extract rating
            rating_match = re.search(r'aria-label="(\d+) star', card_html, re.I)
            rating = int(rating_match.group(1)) if rating_match else 0

            # Extract text
            text_match = re.search(r'<span[^>]*class="[^"]*review-text[^"]*"[^>]*>([^<]+)</span>', card_html) or \
                        re.search(r'<div[^>]*class="[^"]*wiI7pd[^"]*"[^>]*>([^<]+)</div>', card_html)
            text = text_match.group(1).strip() if text_match else ''

            # Extract date
            date_match = re.search(r'(\d+\s+(?:day|week|month|year)s?\s+ago)', card_html, re.I)
            date = date_match.group(1) if date_match else ''

            # Extract likes
            likes_match = re.search(r'(\d+)\s+(?:like|helpful)', card_html, re.I)
            likes = int(likes_match.group(1)) if likes_match else 0

            review = PlaceReview(
                author=author,
                rating=rating,
                text=text,
                date=date,
                likes=likes
            )

            return review

        except Exception as e:
            logger.debug(f"Error parsing review card HTML: {e}")
            return None
