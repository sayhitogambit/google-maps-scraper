"""Google Maps Scraper - Main Entry Point"""
import asyncio, logging, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scraper import GoogleMapsScraper
from config import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def main():
    examples = {
        "1": {"name": "Coffee shops in SF", "input": {"search_query": "coffee shops", "location": "San Francisco, CA", "max_results": 50}},
        "2": {"name": "Restaurants in NYC", "input": {"search_query": "restaurants", "location": "New York, NY", "max_results": 100, "include_reviews": True}},
        "3": {"name": "Hotels in LA", "input": {"search_query": "hotels", "location": "Los Angeles, CA", "max_results": 30}},
    }

    print("\n" + "="*60 + "\nGoogle Maps Scraper\n" + "="*60)
    print("\nSelect an example:"), [print(f"  {k}. {v['name']}") for k, v in examples.items()]

    choice = input("\nChoice (1-3): ").strip()
    input_data = examples.get(choice, examples["1"])["input"]

    config = load_config()
    scraper = GoogleMapsScraper(proxy_config=config['proxy'], rate_limit=config['rate_limit'],
                                 cache_config=config['cache'], output_dir=config['output_dir'])

    results = await scraper.run(input_data, export_formats=['json', 'csv'])
    print(f"\n✓ Scraped {len(results)} places\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(main())
