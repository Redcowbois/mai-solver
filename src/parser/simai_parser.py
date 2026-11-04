from pathlib import Path
from tokens import NoteEvent, NoteType, TimedNoteGroup
import re
from math import pi, sin, cos


def parse_maidata_file(file_path: str | Path) -> dict:
    """Parse a maidata.txt file into metadata, levels, and raw chart strings."""
    with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
        content = f.read()

    pattern = re.compile(r"&([a-zA-Z0-9_]+)=(.*?)(?=\n&|\Z)", re.DOTALL)
    matches = pattern.findall(content)

    chart_data = {
        "metadata": {},
        "levels": {},
        "charts": {}
    }

    for key, value in matches:
        key = key.strip()
        value = value.strip()

        if key.startswith("lv_"):
            diff_idx = int(key.split("_")[1])
            chart_data["levels"][diff_idx] = value
        elif key.startswith("inote_"):
            diff_idx = int(key.split("_")[1])
            chart_data["charts"][diff_idx] = value
        else:
            chart_data["metadata"][key] = value

    return chart_data


# note expression regex
_NOTE_RE = re.compile(
    r"""
    ^
    (?P<button>[1-8])           # button digit
    (?P<mods>[bx]*)             # optional modifiers (b, x, bx, xb)
    (?:
        h\[                     # hold marker
        (?:(?P<hwait>\d+):)?    # optional wait subdivision
        (?P<hdur>\d+)           # duration beats
        \]
    )?
    $                           # must consume the entire fragment
    """,
    re.VERBOSE,
)


def _parse_hold_duration_ms(
    wait_sub: str | None,
    dur_beats: str,
    bpm: float,
    subdivision: int,
) -> tuple[float, float]:
    """Return (wait_ms, hold_duration_ms) from hold bracket values.

    Format is h[wait:dur] where both are in beat counts relative to their
    subdivision, or h[dur] (wait defaults to current subdivision).
    """
    beat_ms = 60_000.0 / bpm

    # The wait subdivision (first number) tells you the note division,
    # the dur (second number) tells you how many of those divisions.
    wait_div = int(wait_sub) if wait_sub else subdivision
    dur_count = int(dur_beats)

    hold_ms = beat_ms * (4.0 / wait_div) * dur_count
    return hold_ms


def parse_chart(chart_str: str) -> list[TimedNoteGroup]:
    """Parse a raw simai chart string into a chronological list of TimedNoteGroups.

    Only TAP and HOLD notes on buttons 1-8 are kept.
    Slides, touch notes, and everything else is silently ignored.
    """
    # Strip all whitespace — it's not meaningful in simai
    chart_str = re.sub(r"\s+", "", chart_str)

    # State
    bpm: float = 120.0
    subdivision: int = 4
    time_ms: float = 0.0

    result: list[TimedNoteGroup] = []

    # Split into comma-separated slots (each comma advances time)
    # But first we need to handle BPM/subdivision directives that can appear
    # anywhere. We'll process the string character-by-character in a light
    # state machine, splitting on commas while extracting directives inline.

    pos = 0
    length = len(chart_str)

    # Accumulates the current beat-slot's text (between commas)
    slot_buf: list[str] = []
    current_slot = ""

    def _flush_slot(slot: str, t: float) -> TimedNoteGroup | None:
        """Parse one comma-slot into a TimedNoteGroup (or None if empty)."""
        if not slot:
            return None

        # Split on "/" for simultaneous notes
        fragments = slot.split("/")
        notes: list[NoteEvent] = []

        for frag in fragments:
            m = _NOTE_RE.match(frag)
            if not m:
                # Not a simple tap/hold on 1-8 → skip (slide, touch, etc.)
                continue

            button = int(m.group("button"))
            mods = m.group("mods") or ""
            is_break = "b" in mods
            is_ex = "x" in mods

            if m.group("hdur") is not None:
                # Hold note
                hold_ms = _parse_hold_duration_ms(
                    m.group("hwait"), m.group("hdur"), bpm, subdivision
                )
                notes.append(NoteEvent(
                    time_ms=t,
                    note_type=NoteType.HOLD,
                    button=button,
                    is_break=is_break,
                    is_ex=is_ex,
                    hold_duration_ms=hold_ms,
                ))
            else:
                # Tap note
                notes.append(NoteEvent(
                    time_ms=t,
                    note_type=NoteType.TAP,
                    button=button,
                    is_break=is_break,
                    is_ex=is_ex,
                ))

        if not notes:
            return None
        return TimedNoteGroup(time_ms=t, notes=notes)

    current_slot = ""

    while pos < length:
        ch = chart_str[pos]

        # --- BPM directive: (number) ---
        if ch == "(":
            end = chart_str.index(")", pos)
            bpm = float(chart_str[pos + 1 : end])
            pos = end + 1
            continue

        # --- Subdivision directive: {number} ---
        if ch == "{":
            end = chart_str.index("}", pos)
            subdivision = int(chart_str[pos + 1 : end])
            pos = end + 1
            continue

        # --- End of chart ---
        if ch == "E" and (pos + 1 >= length or chart_str[pos + 1] not in "12345678"):
            # Flush remaining slot
            group = _flush_slot(current_slot, time_ms)
            if group:
                result.append(group)
            break

        # --- Comma: advance time ---
        if ch == ",":
            group = _flush_slot(current_slot, time_ms)
            if group:
                result.append(group)
            current_slot = ""
            delta = (60_000.0 / bpm) * (4.0 / subdivision)
            time_ms += delta
            pos += 1
            continue

        # --- Everything else: accumulate into current slot ---
        current_slot += ch
        pos += 1

    return result


# main 
if __name__ == "__main__":
    data = parse_maidata_file("data/raw/icecream.txt")
    print("Title:", data["metadata"].get("title"))

    for diff_idx in sorted(data["charts"].keys()):
        chart_str = data["charts"][diff_idx]
        groups = parse_chart(chart_str)

        tap_count = sum(
            1 for g in groups for n in g.notes if n.note_type == NoteType.TAP
        )
        hold_count = sum(
            1 for g in groups for n in g.notes if n.note_type == NoteType.HOLD
        )
        print(f"\n--- Difficulty {diff_idx} (lv {data['levels'].get(diff_idx, '?')}) ---")
        print(f"  {len(groups)} note groups, {tap_count} taps, {hold_count} holds")
        print(f"  First 10 groups:")
        for g in groups[:10]:
            print(f"    {g}")
