import importlib.util
import pathlib

_PATH = pathlib.Path(__file__).parents[3] / "reai_toolkit/utils/monitoring/line_attributions.py"
_spec = importlib.util.spec_from_file_location("line_attributions", _PATH)
la = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(la)

ASSEMBLY = [
    "0x1000\tpush rbp",
    "0x1001\tmov rbp, rsp",
    "0x1004\txor eax, eax",
    "0x1006\tret",
]


def test_disassembly_line_is_offset_by_one_row():
    attributions = la.LineAttributions.of({"0": [2]}, ASSEMBLY)

    assert attributions.addresses_for(2) == [0x1001]
    assert attributions.decompilation_lines_for(0x1001) == [2]


def test_many_to_many_is_sorted_both_ways():
    attributions = la.LineAttributions.of({"2": [4, 1], "0": [4]}, ASSEMBLY)

    assert attributions.addresses_for(4) == [0x1001, 0x1006]
    assert attributions.decompilation_lines_for(0x1006) == [1, 4]


def test_unmappable_rows_are_dropped():
    attributions = la.LineAttributions.of({"x": [1], "3": [1], "-2": [1], "1": None}, ASSEMBLY)

    assert attributions.is_empty()


def test_missing_inputs_are_empty():
    assert la.LineAttributions.of(None, ASSEMBLY).is_empty()
    assert la.LineAttributions.of({"0": [1]}, []).is_empty()
    assert la.LineAttributions().addresses_for(0) == []


def test_parse_address():
    assert la.parse_address("0x401000\tPUSH RBP") == 0x401000
    assert la.parse_address("  0X10 nop") == 0x10
    assert la.parse_address("push rbp") is None
    assert la.parse_address("0xzz nop") is None
    assert la.parse_address("") is None
    assert la.parse_address(None) is None


def test_read_assembly_orders_blocks_by_start():
    blocks = [
        {"min_addr": 0x20, "asm": ["0x20\tret"]},
        {"asm": ["0x99\tnop"]},
        {"min_addr": 0x10, "asm": ["0x10\tpush rbp", "0x11\tmov rbp, rsp"], "destinations": []},
        "junk",
        {"min_addr": 0x30},
    ]

    assert la.read_assembly(blocks) == ["0x10\tpush rbp", "0x11\tmov rbp, rsp", "0x20\tret", "0x99\tnop"]


def test_read_assembly_tolerates_non_lists():
    assert la.read_assembly(None) == []
    assert la.read_assembly({"asm": []}) == []
