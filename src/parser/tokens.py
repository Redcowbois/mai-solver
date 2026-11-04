from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Tuple

class NoteType(Enum):
    TAP = auto()
    HOLD = auto()


@dataclass
class NoteEvent:
    """A single note (tap or hold) at a specific time."""
    time_ms: float
    note_type: NoteType
    button: int             # 1-8
    circle_coord: List[Tuple[float, float]]
    is_break: bool = False
    is_ex: bool = False
    hold_duration_ms: float = 0.0 #hold duration in ms

@dataclass
class TimedNoteGroup:
    """All notes that must be hit simultaneously at one timestamp."""
    time_ms: float
    notes: list[NoteEvent] = field(default_factory=list)

    def __repr__(self) -> str:
        labels = []
        for n in self.notes:
            s = str(n.button)
            if n.is_break:
                s += "b"
            if n.is_ex:
                s += "x"
            if n.note_type == NoteType.HOLD:
                s += f"h({n.hold_duration_ms:.0f}ms)"
            labels.append(s)
        return f"@{self.time_ms:.1f}ms [{'/'.join(labels)}]"
