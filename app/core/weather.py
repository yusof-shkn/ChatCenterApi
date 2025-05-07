import httpx
from typing import Dict, Any


async def get_city_weather(city: str, time: str = "today") -> Dict[str, Any]:
    """
    Fetches weather with better error handling and validation.
    """
    try:
        url = f"https://wttr.in/{city}"
        params = {"format": "j1"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        # Validate API response structure
        if not isinstance(data.get("current_condition"), list) or not isinstance(
            data.get("weather"), list
        ):
            raise ValueError("Invalid API response format")

        # Rest of the code remains the same...

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Location '{city}' not found")
        raise
    except (KeyError, IndexError, ValueError) as e:
        raise ValueError(f"Could not parse weather data: {str(e)}")
