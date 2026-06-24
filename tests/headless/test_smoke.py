import pytest

pytestmark = pytest.mark.headless


def test_binary_loads_with_functions(bv):
    functions = list(bv.functions)
    assert len(functions) > 0
    assert all(hasattr(f, "start") for f in functions)
