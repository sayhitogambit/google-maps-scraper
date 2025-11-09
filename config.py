"""Google Maps Scraper - Configuration with IPRoyal Support"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared.config_helper import load_actor_config

def load_config():
    """Load Google Maps scraper configuration with IPRoyal proxies"""
    return load_actor_config(
        actor_name='google_maps',
        default_country='us',
        default_rate_limit=30,
        default_rate_window=60
    )
