from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from contract import TOOLS, Tool
from plugin.__main__ import IMPLEMENTATIONS
from plugin.puzzles import puzzles

ROOT = Path(__file__).resolve().parent.parent


def test_every_tool_is_implemented() -> None:
    assert set(IMPLEMENTATIONS) == set(Tool) == set(TOOLS)


@pytest.mark.anyio
async def test_the_mcp_server_serves_the_tools(tmp_path: Path) -> None:
    env = {**os.environ, "NANOAGENT_WORKSPACE": str(tmp_path)}
    server = StdioServerParameters(command=sys.executable, args=["-m", "plugin"], cwd=str(ROOT), env=env)
    async with stdio_client(server) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        listed = await session.list_tools()
        assert sorted(tool.name for tool in listed.tools) == sorted(tool.value for tool in Tool)
        puzzle = await session.call_tool("get_puzzle", {"puzzle_id": "m1-0001"})
        assert not puzzle.isError and puzzle.structuredContent["mate_in"] == 1
        key = puzzles()["m1-0001"]["keys"][0]
        played = await session.call_tool("play_moves", {"fen": puzzle.structuredContent["fen"], "moves": [key]})
        assert not played.isError and played.structuredContent["checkmate"] is True
        refused = await session.call_tool("play_moves", {"fen": puzzle.structuredContent["fen"], "moves": ["a1a1"]})
        assert refused.isError


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
