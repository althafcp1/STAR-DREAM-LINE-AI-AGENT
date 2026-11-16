"""
Hotel Accommodation Service (Phase 3: External Tool Integrations & Services)

Retrieves lodging options matching budget tier, calculates room counts and total stay costs.
"""

from typing import Dict, Any, List, Optional
import math
from app.core.tools import HOTEL_DATABASE


class HotelService:
    """
    Client for searching hotels and calculating accommodation pricing.
    """
    def search_accommodations(
        self,
        city: str,
        budget_tier: str = "mid",
        nights: int = 3,
        guests: int = 2
    ) -> Dict[str, Any]:
        clean_city = city.strip().lower()
        tier = budget_tier.strip().lower()
        if tier not in ["budget", "mid", "luxury"]:
            tier = "mid"

        rooms_needed = max(1, math.ceil(guests / 2))
        
        # Check database records
        if clean_city in HOTEL_DATABASE and tier in HOTEL_DATABASE[clean_city]:
            raw_hotels = HOTEL_DATABASE[clean_city][tier]
        else:
            # Fallback for dynamic cities
            tier_defaults = {
                "budget": {"name": f"{city.title()} Central Backpacker Hostel", "rate": 35, "rating": 4.2},
                "mid": {"name": f"Hotel {city.title()} Grand Boutique", "rate": 120, "rating": 4.5},
                "luxury": {"name": f"The Ritz-{city.title()} Luxury & Spa", "rate": 650, "rating": 4.9}
            }
            default_h = tier_defaults[tier]
            raw_hotels = [
                {
                    "name": default_h["name"],
                    "nightly_rate_usd": default_h["rate"],
                    "rating": default_h["rating"],
                    "area": "Downtown Central",
                    "amenities": ["WiFi", "Breakfast", "Air Conditioning"]
                }
            ]

        results = []
        for h in raw_hotels:
            total_cost = h["nightly_rate_usd"] * nights * rooms_needed
            results.append({
                "name": h["name"],
                "area": h.get("area", "Central District"),
                "rating": h.get("rating", 4.3),
                "nightly_rate_usd": h["nightly_rate_usd"],
                "rooms_needed": rooms_needed,
                "total_stay_cost_usd": total_cost,
                "amenities": h.get("amenities", ["WiFi", "24h Desk"])
            })

        return {
            "city": city.title(),
            "budget_tier": tier,
            "nights": nights,
            "guests": guests,
            "rooms_needed": rooms_needed,
            "options_count": len(results),
            "hotels": results
        }

