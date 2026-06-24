import os

import pytest

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "fixtures", "hello.elf")


@pytest.fixture
def bv():
    binaryninja = pytest.importorskip("binaryninja")
    if not os.path.isfile(FIXTURE):
        pytest.skip(f"missing fixture {FIXTURE}")
    with binaryninja.load(os.path.abspath(FIXTURE)) as view:
        yield view
