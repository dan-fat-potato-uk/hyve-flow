import pytest

from hyve_flow.models import (
    DataSource,
    get_data_source,
    get_registered_data_sources,
    register_data_source,
)
from hyve_flow.models.data_source import _DATA_SOURCES


@pytest.fixture(autouse=True)
def isolated_registry():
    _DATA_SOURCES.clear()
    yield
    _DATA_SOURCES.clear()


class ExampleDataSource(DataSource):
    name = "example"

    def build_init_family(self, config, **kwargs):
        return {"family": "init", "config": config, "kwargs": kwargs}

    def build_main_family(self, config, **kwargs):
        return {"family": "main", "config": config, "kwargs": kwargs}


def test_none_resolves_a_registered_default_data_source() -> None:
    register_data_source("default")(ExampleDataSource)

    assert isinstance(get_data_source("default"), ExampleDataSource)
    assert isinstance(get_data_source(None), ExampleDataSource)


def test_custom_data_source_registers_without_editing_main_families() -> None:
    register_data_source(ExampleDataSource)
    source = get_data_source("example")
    assert source.build_init_family("cfg", queued=True)["family"] == "init"
    assert source.build_main_family("cfg", queued=True)["family"] == "main"


def test_string_decorator_registration_uses_normalized_name() -> None:
    @register_data_source("Decorated Data Source")
    class DecoratedDataSource(DataSource):
        def build_init_family(self, config, **kwargs):
            return {"family": "decorated-init", "config": config, "kwargs": kwargs}

        def build_main_family(self, config, **kwargs):
            return {"family": "decorated-main", "config": config, "kwargs": kwargs}

    source = get_data_source("decorated")
    assert source.build_init_family("cfg")["family"] == "decorated-init"
    assert source.build_main_family("cfg")["family"] == "decorated-main"


def test_registered_sources_are_unique_and_include_default() -> None:
    register_data_source("default")(ExampleDataSource)
    register_data_source("duplicate")(ExampleDataSource)

    sources = get_registered_data_sources()
    assert len(sources) == len({id(cls) for cls in sources})
    assert sources == [ExampleDataSource]