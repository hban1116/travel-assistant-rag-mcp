"""MCP weather server — exposes get_forecast via FastMCP over stdio."""
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("weather")

DEFAULT_LAT, DEFAULT_LON = 1.3521, 103.8198


@mcp.tool()
async def get_forecast(city: str = "Singapore", days: int = 3) -> dict:
    """Get a N-day weather forecast for a city using Open-Meteo."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": DEFAULT_LAT,
                "longitude": DEFAULT_LON,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "forecast_days": days,
                "timezone": "Asia/Singapore",
            },
        )
        r.raise_for_status()
        d = r.json()["daily"]

    return {
        "city": city,
        "days": [
            {
                "date": d["time"][i],
                "tmax_c": d["temperature_2m_max"][i],
                "tmin_c": d["temperature_2m_min"][i],
                "rain_mm": d["precipitation_sum"][i],
                "weathercode": d["weathercode"][i],
            }
            for i in range(len(d["time"]))
        ],
    }


if __name__ == "__main__":
    mcp.run()