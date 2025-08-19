"""
Capabilities Package

MCP capability negotiation and management.
"""

from .negotiator import CapabilityNegotiator
from .registry import CapabilityRegistry

__all__ = ["CapabilityNegotiator", "CapabilityRegistry"]