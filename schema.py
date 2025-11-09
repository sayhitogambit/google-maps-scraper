"""
Google Maps Scraper - Input/Output Schemas
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class GoogleMapsScraperInput(BaseModel):
    """Input schema for Google Maps Scraper"""

    search_query: str = Field(
        ...,
        description="Search query (e.g., 'restaurants in New York')",
        example="coffee shops in San Francisco"
    )

    location: Optional[str] = Field(
        None,
        description="Location to search in",
        example="New York, NY"
    )

    coordinates: Optional[Dict[str, float]] = Field(
        None,
        description="Coordinates for search center"
    )

    max_results: int = Field(
        100,
        ge=1,
        le=1000,
        description="Maximum results to scrape"
    )

    include_reviews: bool = Field(
        False,
        description="Include reviews for each place"
    )

    max_reviews_per_place: int = Field(
        50,
        ge=0,
        le=500,
        description="Maximum reviews per place"
    )

    language: str = Field(
        "en",
        description="Language code (en, es, fr, etc.)"
    )


class PlaceReview(BaseModel):
    """Google Maps review schema"""
    author: str
    rating: int  # 1-5
    text: str
    date: str
    likes: int = 0
    photos: List[str] = []


class GoogleMapsPlace(BaseModel):
    """Google Maps place schema"""
    place_id: str
    name: str
    category: Optional[str] = None
    address: str
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    total_reviews: int = 0
    price_level: Optional[str] = None  # $, $$, $$$, $$$$
    opening_hours: Dict[str, Any] = {}
    coordinates: Dict[str, float] = {}
    plus_code: Optional[str] = None
    images: List[str] = []
    reviews: List[PlaceReview] = []
    attributes: List[str] = []
    popular_times: Dict[str, Any] = {}
    share_link: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                "name": "Great Coffee Shop",
                "category": "Coffee shop",
                "address": "123 Main St, San Francisco, CA",
                "phone": "+1 415-555-0123",
                "rating": 4.5,
                "total_reviews": 250
            }
        }
