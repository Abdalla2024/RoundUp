import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apisupport import FakeStorage, Keys, default_run, make_app, make_client  # noqa: E402


@pytest.fixture(scope="session")
def keys():
    return Keys()


@pytest.fixture
def storage():
    return FakeStorage()


@pytest.fixture
def client(keys, storage):
    with make_client(make_app(keys=keys, storage=storage)) as c:
        yield c


@pytest.fixture
def run(client):
    return default_run(client)
