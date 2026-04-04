import pytest
from aion.storage import init_db

@pytest.fixture(autouse=True)
def setup_db():
    init_db()