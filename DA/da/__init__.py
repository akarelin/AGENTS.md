"""DA (DebilAgent) - Personal multi-agent system built on Anthropic SDK."""

try:
    from importlib.metadata import version
    __version__ = version("DA")
except Exception:
    __version__ = "0.0.0"
