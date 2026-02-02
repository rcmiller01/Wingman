"""Collectors package."""
from app.collectors.fact_collector import fact_collector, FactCollector
from app.collectors.log_collector import log_collector, LogCollector

__all__ = [
    "fact_collector",
    "FactCollector",
    "log_collector",
    "LogCollector",
]
