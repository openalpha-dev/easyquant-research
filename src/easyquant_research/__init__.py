"""EasyQuant Research: open-source MCP connector and Agent Skills for the EasyQuant research engine.

The engine and its data stay hosted; this package open-sources the client side — a stdio MCP
server (offline reference tools + a bridge to the hosted research MCP), a CLI, and installable
Agent Skills. Every tool is historical research only: no orders, no live trading, no fund
accounts, no API-key management.
"""
from ._resources import data_root, load_tools
from .client import Client, ResearchError

__all__ = ["Client", "ResearchError", "data_root", "load_tools"]
__version__ = "0.1.1"