from typing import Dict, List, Optional

# The model numbered the sequencer trace, which runs one line ahead of the blocks' assembly,
# so disassembly line n is assembly line n + 1.
DISASSEMBLY_ROW_OFFSET = 1


def read_assembly(basic_blocks) -> List[str]:
    """Flatten the untyped `basic_blocks` of GET /v3/functions/{id}/blocks into assembly lines, ordered by block start."""
    if not isinstance(basic_blocks, list):
        return []
    blocks = [b for b in basic_blocks if isinstance(b, dict)]
    blocks.sort(key=lambda b: b["min_addr"] if isinstance(b.get("min_addr"), int) else float("inf"))
    assembly = []
    for block in blocks:
        asm = block.get("asm")
        if isinstance(asm, list):
            assembly.extend(str(line) for line in asm if isinstance(line, (str, int, float)))
    return assembly


def parse_address(assembly_line) -> Optional[int]:
    if not isinstance(assembly_line, str) or not assembly_line.strip():
        return None
    head = assembly_line.split(None, 1)[0]
    if not head.lower().startswith("0x"):
        return None
    try:
        return int(head, 16)
    except ValueError:
        return None


class LineAttributions:
    """Which instructions fed which AI decompilation lines (0-based on both sides, many-to-many)."""

    def __init__(self, addresses_by_line: Optional[Dict[int, List[int]]] = None,
                 lines_by_address: Optional[Dict[int, List[int]]] = None):
        self._addresses_by_line = addresses_by_line or {}
        self._lines_by_address = lines_by_address or {}

    @classmethod
    def of(cls, disassembly_to_decompilation, assembly) -> "LineAttributions":
        if not disassembly_to_decompilation or not assembly:
            return cls()
        by_line: Dict[int, set] = {}
        by_address: Dict[int, set] = {}
        for raw_line, decompilation_lines in disassembly_to_decompilation.items():
            address = cls._address_of_row(assembly, raw_line)
            if address is None or not decompilation_lines:
                continue
            for line in decompilation_lines:
                if line is None:
                    continue
                by_line.setdefault(int(line), set()).add(address)
                by_address.setdefault(address, set()).add(int(line))
        return cls(
            {k: sorted(v) for k, v in by_line.items()},
            {k: sorted(v) for k, v in by_address.items()},
        )

    def addresses_for(self, decompilation_line: int) -> List[int]:
        return self._addresses_by_line.get(decompilation_line, [])

    def decompilation_lines_for(self, address: int) -> List[int]:
        return self._lines_by_address.get(address, [])

    def is_empty(self) -> bool:
        return not self._addresses_by_line

    @staticmethod
    def _address_of_row(assembly, raw_line) -> Optional[int]:
        try:
            row = int(raw_line) + DISASSEMBLY_ROW_OFFSET
        except (TypeError, ValueError):
            return None
        if row < 0 or row >= len(assembly):
            return None
        return parse_address(assembly[row])
