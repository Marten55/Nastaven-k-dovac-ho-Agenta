#!/usr/bin/env python3
"""Konci-do-konca kontrola: spusti woo-mcp ako samostatny proces cez stdio,
spravi MCP handshake, vypise nastroje a zavola dva z nich.

Spustenie:  uv run python smoke_stdio.py
Nepotrebuje e-shop - bezi v rezime fixtures.
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.stdout.reconfigure(encoding="utf-8")


async def main() -> int:
    parametre = StdioServerParameters(
        command="uv",
        args=["run", "woo-mcp"],
        env={**os.environ, "WOO_MODE": "fixtures"},
    )

    async with stdio_client(parametre) as (citaj, zapis):
        async with ClientSession(citaj, zapis) as session:
            init = await session.initialize()
            print(f"handshake OK -> server '{init.server_info.name}' "
                  f"v{init.server_info.version or '0.1.0'}")

            nastroje = (await session.list_tools()).tools
            print(f"\nnastroje ({len(nastroje)}):")
            for n in nastroje:
                znacka = "R" if (n.annotations and n.annotations.read_only_hint) else "W"
                print(f"  [{znacka}] {n.name:16} {n.description.splitlines()[0]}")

            stav = json.loads((await session.call_tool("server_status", {})).content[0].text)
            print(f"\nserver_status -> rezim={stav['rezim']}, zapis={stav['zapis_povoleny']}")

            audit = json.loads((await session.call_tool("audit_seo", {})).content[0].text)
            print(f"audit_seo     -> skontrolovanych {audit['skontrolovanych']}, "
                  f"s problemom {audit['s_problemom']}")
            for nalez in audit["nalezy"]:
                print(f"   - {nalez['sku']:12} {len(nalez['problemy'])} problem(ov)")

            zapis_test = json.loads((await session.call_tool(
                "update_product", {"product_id": 101, "zmeny": {"stock_quantity": 99}}
            )).content[0].text)
            print(f"\nupdate_product -> vykonane={zapis_test['vykonane']} "
                  f"(spravne False, lebo rezim je fixtures)")

    print("\nVSETKO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
