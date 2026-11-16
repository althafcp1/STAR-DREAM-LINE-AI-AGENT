"""
Core Tools for the AI Travel Planning Agent (📘 Lesson 2: 2–4 Clearly Described Tools)

Each tool provides:
1. Exact function signature with type hints.
2. Comprehensive docstring explaining what it does, its arguments, and its return values.
3. Input validation with informative errors for self-correction (📘 L2).
"""

from typing import Dict, Any, List, Optional
import math


class ToolError(Exception):
    """Raised when a tool execution encounters an invalid input or failure."""
    pass


# Curated offline knowledge database for reliable execution and tests
DESTINATION_DATABASE: Dict[str, Dict[str, Any]] = {
    "tokyo": {
        "country": "Japan",
        "currency": "JPY",
        "attractions": [
            {"name": "Senso-ji Temple", "category": "culture", "cost_usd": 0, "duration_hours": 2.0, "best_time": "Morning"},
            {"name": "Meiji Shrine & Yoyogi Park", "category": "nature", "cost_usd": 0, "duration_hours": 2.5, "best_time": "Morning"},
            {"name": "Shibuya Crossing & Hachiko", "category": "city", "cost_usd": 0, "duration_hours": 1.5, "best_time": "Evening"},
            {"name": "Akihabara Electric Town", "category": "shopping", "cost_usd": 30, "duration_hours": 3.0, "best_time": "Afternoon"},
            {"name": "Tokyo Skytree", "category": "sightseeing", "cost_usd": 25, "duration_hours": 2.0, "best_time": "Sunset"}
        ],
        "weather": {"avg_temp_c": 18, "condition": "Partly Cloudy", "rain_chance_pct": 20, "advisory": "Comfortable walking weather. Bring a light jacket."}
    },
    "paris": {
        "country": "France",
        "currency": "EUR",
        "attractions": [
            {"name": "Eiffel Tower", "category": "sightseeing", "cost_usd": 35, "duration_hours": 2.5, "best_time": "Sunset"},
            {"name": "Louvre Museum", "category": "culture", "cost_usd": 22, "duration_hours": 4.0, "best_time": "Morning"},
            {"name": "Notre-Dame & Latin Quarter", "category": "culture", "cost_usd": 0, "duration_hours": 2.0, "best_time": "Afternoon"},
            {"name": "Montmartre & Sacré-Cœur", "category": "culture", "cost_usd": 0, "duration_hours": 2.5, "best_time": "Morning"},
            {"name": "Seine River Cruise", "category": "relaxation", "cost_usd": 18, "duration_hours": 1.5, "best_time": "Evening"}
        ],
        "weather": {"avg_temp_c": 16, "condition": "Mild / Breezy", "rain_chance_pct": 35, "advisory": "Carry a compact umbrella for scattered showers."}
    },
    "jaipur": {
        "country": "India",
        "currency": "INR",
        "attractions": [
            {"name": "Amber Fort", "category": "culture", "cost_usd": 7, "duration_hours": 3.5, "best_time": "Morning"},
            {"name": "Hawa Mahal (Palace of Winds)", "category": "sightseeing", "cost_usd": 3, "duration_hours": 1.5, "best_time": "Morning"},
            {"name": "City Palace", "category": "culture", "cost_usd": 10, "duration_hours": 2.5, "best_time": "Afternoon"},
            {"name": "Jantar Mantar Observatory", "category": "science", "cost_usd": 4, "duration_hours": 1.5, "best_time": "Afternoon"},
            {"name": "Nahargarh Fort Sunset View", "category": "sightseeing", "cost_usd": 5, "duration_hours": 2.0, "best_time": "Sunset"}
        ],
        "weather": {"avg_temp_c": 28, "condition": "Sunny & Warm", "rain_chance_pct": 5, "advisory": "Wear sunscreen, sunglasses, and stay hydrated."}
    }
}

HOTEL_DATABASE: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "tokyo": {
        "budget": [
            {"name": "Nine Hours Shinjuku Capsule", "nightly_rate_usd": 45, "rating": 4.3, "area": "Shinjuku", "amenities": ["WiFi", "Lockers", "24h Desk"]},
            {"name": "Khaosan Tokyo Origami Hostel", "nightly_rate_usd": 38, "rating": 4.5, "area": "Asakusa", "amenities": ["WiFi", "Shared Kitchen", "Lounge"]}
        ],
        "mid": [
            {"name": "Hotel Gracery Shinjuku (Godzilla)", "nightly_rate_usd": 130, "rating": 4.4, "area": "Kabukicho", "amenities": ["WiFi", "Restaurant", "City View"]},
            {"name": "Mitsui Garden Hotel Ginza", "nightly_rate_usd": 160, "rating": 4.6, "area": "Ginza", "amenities": ["WiFi", "Breakfast", "Top Floor Bath"]}
        ],
        "luxury": [
            {"name": "Aman Tokyo", "nightly_rate_usd": 850, "rating": 4.9, "area": "Otemachi", "amenities": ["Spa", "Fine Dining", "Panoramic Views"]},
            {"name": "Park Hyatt Tokyo", "nightly_rate_usd": 650, "rating": 4.8, "area": "Nishi-Shinjuku", "amenities": ["Pool", "Jazz Bar", "Luxury Spa"]}
        ]
    },
    "paris": {
        "budget": [
            {"name": "Generator Hostel Paris", "nightly_rate_usd": 50, "rating": 4.2, "area": "10th Arr.", "amenities": ["Rooftop Bar", "WiFi", "Lockers"]},
            {"name": "St Christopher's Inn Canal", "nightly_rate_usd": 45, "rating": 4.1, "area": "19th Arr.", "amenities": ["WiFi", "Waterfront Terrace"]}
        ],
        "mid": [
            {"name": "Hotel Monge (Quartier Latin)", "nightly_rate_usd": 175, "rating": 4.7, "area": "5th Arr.", "amenities": ["Hamam", "WiFi", "Breakfast"]},
            {"name": "CitizenM Paris Gare de Lyon", "nightly_rate_usd": 150, "rating": 4.5, "area": "12th Arr.", "amenities": ["Modern Tech", "Rooftop Lounge"]}
        ],
        "luxury": [
            {"name": "Le Meurice - Dorchester", "nightly_rate_usd": 950, "rating": 4.9, "area": "Tuileries", "amenities": ["Michelin Dining", "Historic Luxury"]},
            {"name": "Hôtel Plaza Athénée", "nightly_rate_usd": 1100, "rating": 4.9, "area": "Montaigne", "amenities": ["Haute Couture Suite", "Dior Spa"]}
        ]
    },
    "jaipur": {
        "budget": [
            {"name": "Zostel Jaipur", "nightly_rate_usd": 15, "rating": 4.6, "area": "Old City", "amenities": ["WiFi", "Rooftop Cafe", "Social Events"]},
            {"name": "Moustache Hostel Jaipur", "nightly_rate_usd": 18, "rating": 4.5, "area": "MI Road", "amenities": ["Pool", "WiFi", "Courtyard"]}
        ],
        "mid": [
            {"name": "Shahpura House (Heritage)", "nightly_rate_usd": 70, "rating": 4.5, "area": "Bani Park", "amenities": ["Heritage Pool", "Spa", "Restaurant"]},
            {"name": "Alsisar Haveli Heritage Hotel", "nightly_rate_usd": 85, "rating": 4.6, "area": "Sansar Chandra Rd", "amenities": ["Garden", "Fresco Art", "Pool"]}
        ],
        "luxury": [
            {"name": "The Oberoi Rajvilas", "nightly_rate_usd": 750, "rating": 4.9, "area": "Goner Rd", "amenities": ["Private Villas", "Luxury Spa", "Peacock Gardens"]},
            {"name": "Rambagh Palace (Taj)", "nightly_rate_usd": 900, "rating": 5.0, "area": "Bhawani Singh Rd", "amenities": ["Royal Butler", "Polo Lounge", "Historic Suites"]}
        ]
    }
}


# =====================================================================
# TOOL 1: Destination & Attractions Search (📘 L2)
# =====================================================================
def search_destinations_and_attractions(city: str, category: str = "all") -> Dict[str, Any]:
    """
    Search for top tourist sights, attractions, and cultural activities in a destination city.

    Args:
        city: The name of the destination city (e.g. 'Tokyo', 'Paris', 'Jaipur').
        category: Optional category filter ('culture', 'sightseeing', 'nature', 'shopping', or 'all').

    Returns:
        A dictionary containing the destination metadata and a list of attraction objects.

    Raises:
        ToolError: If the city is unrecognized or empty.
    """
    if not city or not city.strip():
        raise ToolError("City parameter cannot be empty. Please provide a valid city name.")
    
    clean_city = city.strip().lower()
    
    # Error simulation / Typo detection (📘 L2 Error Handling)
    if clean_city not in DESTINATION_DATABASE:
        suggestions = [c.title() for c in DESTINATION_DATABASE.keys() if c.startswith(clean_city[:2])]
        hint = f" Did you mean: {', '.join(suggestions)}?" if suggestions else " Supported demo cities: Tokyo, Paris, Jaipur."
        raise ToolError(f"Destination '{city}' is currently not in our verified registry.{hint}")
    
    data = DESTINATION_DATABASE[clean_city]
    attractions = data["attractions"]
    
    if category and category.lower() != "all":
        filtered = [a for a in attractions if a["category"].lower() == category.lower()]
        if not filtered:
            # Fallback gracefully with all attractions if specific filter yielded 0
            filtered = attractions
    else:
        filtered = attractions
        
    return {
        "city": clean_city.title(),
        "country": data["country"],
        "currency": data["currency"],
        "total_attractions_found": len(filtered),
        "attractions": filtered
    }


# =====================================================================
# TOOL 2: Weather Forecast (📘 L2)
# =====================================================================
def get_weather_forecast(city: str, days: int = 5) -> Dict[str, Any]:
    """
    Retrieve weather forecast information and travel advisories for a given destination.

    Args:
        city: Destination city name (e.g. 'Tokyo', 'Paris', 'Jaipur').
        days: Number of forecast days to inspect (between 1 and 14).

    Returns:
        A dictionary with average temperature in Celsius, conditions, rain probability, and advisory.

    Raises:
        ToolError: If days count is outside 1-14 or city is not found.
    """
    if days < 1 or days > 14:
        raise ToolError(f"Forecast days must be between 1 and 14. Received: {days}")
    
    clean_city = city.strip().lower()
    if clean_city not in DESTINATION_DATABASE:
        raise ToolError(f"Cannot retrieve weather for '{city}'. Destination unrecognized.")
    
    weather_info = DESTINATION_DATABASE[clean_city]["weather"]
    return {
        "city": clean_city.title(),
        "forecast_days": days,
        "temperature_celsius": weather_info["avg_temp_c"],
        "condition": weather_info["condition"],
        "precipitation_chance_percent": weather_info["rain_chance_pct"],
        "travel_advisory": weather_info["advisory"]
    }


# =====================================================================
# TOOL 3: Hotel Search & Pricing (📘 L2)
# =====================================================================
def search_hotels(city: str, budget_tier: str = "mid", nights: int = 3, guests: int = 2) -> Dict[str, Any]:
    """
    Find accommodation options matching destination, budget tier, and duration.

    Args:
        city: Destination city (e.g. 'Tokyo', 'Paris', 'Jaipur').
        budget_tier: One of 'budget', 'mid', or 'luxury'.
        nights: Number of nights for the stay (must be >= 1).
        guests: Number of traveling guests (must be >= 1).

    Returns:
        A dictionary with available hotel recommendations and calculated total costs.

    Raises:
        ToolError: If budget_tier is invalid, nights/guests < 1, or city not found.
    """
    if nights < 1:
        raise ToolError(f"Stay nights must be at least 1. Received: {nights}")
    if guests < 1:
        raise ToolError(f"Guests count must be at least 1. Received: {guests}")
    
    valid_tiers = ["budget", "mid", "luxury"]
    clean_tier = budget_tier.strip().lower()
    if clean_tier not in valid_tiers:
        raise ToolError(f"Invalid budget_tier '{budget_tier}'. Must be one of: {valid_tiers}")
    
    clean_city = city.strip().lower()
    if clean_city not in HOTEL_DATABASE:
        raise ToolError(f"No hotel records available for '{city}'.")
    
    tier_hotels = HOTEL_DATABASE[clean_city].get(clean_tier, [])
    # Calculate total pricing based on nights & estimated rooms (2 guests per room)
    rooms_needed = max(1, math.ceil(guests / 2))
    
    results = []
    for h in tier_hotels:
        total_cost = h["nightly_rate_usd"] * nights * rooms_needed
        results.append({
            "name": h["name"],
            "rating": h["rating"],
            "area": h["area"],
            "nightly_rate_usd": h["nightly_rate_usd"],
            "rooms_needed": rooms_needed,
            "total_stay_cost_usd": total_cost,
            "amenities": h["amenities"]
        })
        
    return {
        "city": clean_city.title(),
        "budget_tier": clean_tier,
        "nights": nights,
        "guests": guests,
        "options_count": len(results),
        "hotels": results
    }


# =====================================================================
# TOOL 4: Budget Allocation & Calculator (📘 L2)
# =====================================================================
def calculate_budget_allocation(
    total_budget: float,
    stay_cost: float,
    activities_cost: float = 0.0,
    days: int = 3,
    guests: int = 1
) -> Dict[str, Any]:
    """
    Compute daily allowances, food, transport, and emergency buffer from the trip budget.

    Args:
        total_budget: Total funds allotted for the trip in USD.
        stay_cost: Total accommodation cost for the trip in USD.
        activities_cost: Estimated sightseeing and attractions tickets in USD.
        days: Trip duration in days (minimum 1).
        guests: Number of travelers.

    Returns:
        Detailed financial breakdown including remaining funds, daily per-person food/transit allowance,
        and budget status.

    Raises:
        ToolError: If total_budget <= 0 or stay_cost exceeds total_budget.
    """
    if total_budget <= 0:
        raise ToolError(f"Total budget must be a positive number. Received: ${total_budget}")
    if days < 1:
        raise ToolError(f"Trip duration must be at least 1 day. Received: {days}")
    
    committed_costs = stay_cost + activities_cost
    if committed_costs > total_budget:
        deficit = committed_costs - total_budget
        raise ToolError(
            f"Overbudget Warning: Stay (${stay_cost}) + Activities (${activities_cost}) = ${committed_costs}, "
            f"which exceeds the total budget (${total_budget}) by ${deficit:.2f}. "
            "Please select a cheaper hotel tier or adjust trip duration."
        )
    
    remaining = total_budget - committed_costs
    # Allocate remaining: 15% emergency buffer, 55% food & dining, 30% local transit & incidental
    emergency_buffer = round(remaining * 0.15, 2)
    spendable_remaining = remaining - emergency_buffer
    
    food_budget = round(spendable_remaining * 0.60, 2)
    local_transit = round(spendable_remaining * 0.40, 2)
    
    daily_per_person_food = round(food_budget / (days * max(1, guests)), 2)
    daily_transit = round(local_transit / days, 2)
    
    return {
        "total_budget_usd": total_budget,
        "stay_cost_usd": stay_cost,
        "activities_cost_usd": activities_cost,
        "emergency_buffer_usd": emergency_buffer,
        "estimated_food_total_usd": food_budget,
        "estimated_local_transit_usd": local_transit,
        "daily_food_per_person_usd": daily_per_person_food,
        "daily_transit_usd": daily_transit,
        "total_allocated_usd": stay_cost + activities_cost + emergency_buffer + food_budget + local_transit,
        "is_healthy_budget": emergency_buffer >= (total_budget * 0.05)
    }


# =====================================================================
# TOOL REGISTRY (📘 L2 Tool Schemas for Agents)
# =====================================================================
TOOL_REGISTRY: Dict[str, Any] = {
    "search_destinations_and_attractions": search_destinations_and_attractions,
    "get_weather_forecast": get_weather_forecast,
    "search_hotels": search_hotels,
    "calculate_budget_allocation": calculate_budget_allocation
}

TOOL_DESCRIPTIONS = [
    {
        "name": "search_destinations_and_attractions",
        "description": "Searches for top tourist attractions, culture sights, ticket prices, and opening hours for a city.",
        "parameters": {
            "city": "string (required, e.g. 'Tokyo', 'Paris', 'Jaipur')",
            "category": "string (optional: 'culture', 'sightseeing', 'nature', 'shopping', or 'all')"
        }
    },
    {
        "name": "get_weather_forecast",
        "description": "Retrieves weather conditions, average temperature in Celsius, precipitation chance, and packing advice.",
        "parameters": {
            "city": "string (required, e.g. 'Tokyo')",
            "days": "integer (optional, default 5, 1-14)"
        }
    },
    {
        "name": "search_hotels",
        "description": "Finds accommodation options with prices, ratings, and amenities filtered by budget category.",
        "parameters": {
            "city": "string (required)",
            "budget_tier": "string (required: 'budget', 'mid', or 'luxury')",
            "nights": "integer (optional, default 3)",
            "guests": "integer (optional, default 2)"
        }
    },
    {
        "name": "calculate_budget_allocation",
        "description": "Calculates complete budget distribution: stay cost, food allowance, transit, and emergency buffer.",
        "parameters": {
            "total_budget": "float (required, e.g. 1000.0)",
            "stay_cost": "float (required, e.g. 450.0)",
            "activities_cost": "float (optional, default 0.0)",
            "days": "integer (optional, default 3)",
            "guests": "integer (optional, default 2)"
        }
    }
]

