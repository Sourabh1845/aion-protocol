import os
import tempfile
from pathlib import Path

import pytest

# Every run owns its store: nothing here may touch the developer's real ~/.aion.
os.environ["AION_HOME"] = str(Path(tempfile.mkdtemp(prefix="aion-tests-")))

from aion.storage import init_db  # noqa: E402


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
