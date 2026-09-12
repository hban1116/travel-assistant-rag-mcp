"""MCP currency server — exposes convert via FastMCP over stdio."""
from mcp.server.fastmcp import FastMCP
import httpx

mcp = FastMCP("currency")


@mcp.tool()
async def convert(amount: float, from_currency: str, to_currency: str) -> dict:
    """Convert an amount between two currencies via frankfurter.app."""
    frm = from_currency.upper()
    to = to_currency.upper()
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            "https://api.frankfurter.dev/v1/latest",
            params={"amount": amount, "from": frm, "to": to},
        )
        r.raise_for_status()
        data = r.json()

    converted = data["rates"][to]
    rate = converted / amount if amount else None
    return {
        "amount": amount,
        "from": frm,
        "to": to,
        "rate": rate,
        "converted": converted,
        "date": data.get("date"),
    }


if __name__ == "__main__":
    mcp.run()