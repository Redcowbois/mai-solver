from enum import Enum
from typing import Dict, List, Tuple
import math

class NotePosition(Enum):
    BUTTON1 = 0
    BUTTON2 = 1
    BUTTON3 = 2
    BUTTON4 = 3
    BUTTON5 = 4
    BUTTON6 = 5
    BUTTON7 = 6
    BUTTON8 = 7
    A1 = 8
    A2 = 9
    A3 = 10
    A4 = 11
    A5 = 12
    A6 = 13
    A7 = 14
    A8 = 15

def _calculate_theta_pos(r : float, theta : float) -> Tuple[float, float]:
    """
    Args:
        r: Radial distance from the screen center (normalized, e.g., 1.0 for perimeter buttons).
        theta: Angle in radians (standard polar angle, where 0 is at 3 o'clock).
    Returns:
        Tuple[float, float]: The (x, y) coordinates corresponding to the polar input.
    """
    x = round(r * math.cos(theta), 4)
    y = round(r * math.sin(theta), 4)
    return (x, y)

# Set radiuses for different touch sensors
RADII: Dict[str, float] = {
    "BUTTON": 1.00,
    "A": 0.88,
    "B": 0.72,
    "E": 0.54,
    "D": 0.36,
    "C": 0.00,
}

# possible angles for buttons in pixel
BUTTON_ANGLES: Dict[int, float] = {
    k: (3 * math.pi / 8) - (k - 1) * (math.pi / 4) for k in range(1, 9)
}

# valid touch points for tap and hold
PRECOMPUTED_PERIMETER_CANDIDATES: Dict[int, List[Tuple[float, float]]] = {
    k: [
        _calculate_theta_pos(RADII["BUTTON"], BUTTON_ANGLES[k]),  # Switch c_contact
        _calculate_theta_pos(RADII["A"], BUTTON_ANGLES[k]),       # Glass touch contact
    ]
    for k in range(1, 9)
}