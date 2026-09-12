"""Async MCP client — spawns stdio servers and calls their tools."""
import asyncio
import json
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).parent


async def _call(server_script: str, tool: str, args: dict):
    params = StdioServerParameters(
        command=sys.executable,   # use venv python, not system python
        args=[str(ROOT / "mcp_servers" / server_script)],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            if not result.content:
                return {"error": "empty MCP response"}
            text = result.content[0].text
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text}


async def call_weather(city: str = "Singapore", days: int = 3):
    return await _call("weather_server.py", "get_forecast", {"city": city, "days": days})


async def call_currency(amount: float, frm: str, to: str):
    return await _call("currency_server.py", "convert",
                       {"amount": amount, "from_currency": frm, "to_currency": to})


def get_weather_sync(city: str = "Singapore", days: int = 3):
    return asyncio.run(call_weather(city, days))


def convert_currency_sync(amount: float, frm: str, to: str):
    return asyncio.run(call_currency(amount, frm, to))


if __name__ == "__main__":
    print("WEATHER:", get_weather_sync("Singapore", 3))
    print("CURRENCY:", convert_currency_sync(50000, "INR", "SGD"))