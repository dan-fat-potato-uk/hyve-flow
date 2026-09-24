from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pyflow as pf
else:
    pf = Any

_DATA_SOURCES: dict[str, type[DataSource]] = {}


def _normalise_source_name(name: Any) -> str:
    candidate = str(name).strip().replace(" ", "").lower()
    for suffix in ("data_source", "datasource"):
        if candidate.endswith(suffix):
            candidate = candidate[: -len(suffix)]
            break
    return candidate


class DataSource(ABC):
    """Extension point for reforecast data sources."""

    name: str = ""

    @abstractmethod
    def build_init_family(self, config: Any, **kwargs: Any) -> pf.Family:
        """Build a family for one-time init tasks."""

    @abstractmethod
    def build_main_family(self, config: Any, **kwargs: Any) -> pf.Family:
        """Build a family for per-run tasks."""


def register_data_source(source: type[DataSource] | str):
    """Register a data source implementation by class or name."""
    if isinstance(source, str):

        def decorator(cls: type[DataSource]) -> type[DataSource]:
            if not isinstance(cls, type) or not issubclass(cls, DataSource):
                raise TypeError("source must be a DataSource subclass")

            key = _normalise_source_name(source)
            _DATA_SOURCES[key] = cls
            return cls

        return decorator

    if not isinstance(source, type) or not issubclass(source, DataSource):
        raise TypeError("source must be a DataSource subclass")

    key = _normalise_source_name(getattr(source, "name", None) or source.__name__)
    _DATA_SOURCES[key] = source
    return source


def get_registered_data_sources() -> list[type[DataSource]]:
    """Return all registered data source classes in insertion order."""
    return list(dict.fromkeys(_DATA_SOURCES.values()))


def get_data_source(name: str | DataSource | type[DataSource] | None) -> DataSource:
    """Resolve a registered data source and return an instance."""
    if name is None:
        name = "default"

    if isinstance(name, DataSource):
        return name

    if isinstance(name, type) and issubclass(name, DataSource):
        return name()

    key = _normalise_source_name(name)
    if key not in _DATA_SOURCES:
        available = ", ".join(sorted(_DATA_SOURCES)) or "none"
        raise KeyError(f"Unknown data source '{name}'. Available sources: {available}")

    return _DATA_SOURCES[key]()


__all__ = [
    "_DATA_SOURCES",
    "DataSource",
    "get_data_source",
    "get_registered_data_sources",
    "register_data_source",
]
