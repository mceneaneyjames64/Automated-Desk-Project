from math import atan2, degrees, acos, sqrt


def vector_to_degrees(x, y):
    """Convert coordinates into an angle in degrees."""
    angle = degrees(atan2(y, x))
    if angle < 0:
        angle += 360
    return angle


def z_axis_to_degrees(z: float, g: float = 9.81) -> float:
    """
    Convert a Z-axis accelerometer reading to an angle in degrees.

    Convention
    ----------
    - 0°   : sensor is upside down  (Z ≈ −g, pointing away from gravity)
    - 90°  : sensor is perpendicular to the ground (Z ≈ 0)
    - 180° : sensor is right-side up (Z ≈ +g, pointing toward gravity)

    The raw formula is:
        angle = degrees( acos( clamp(z / g, -1, 1) ) )   → 0° … 180°

    Then we remap so that upside-down = 0°:
        remapped = 180° − angle

    Parameters
    ----------
    z : float
        Acceleration along the Z axis in m/s².
    g : float
        Local gravitational acceleration in m/s² (default 9.81).

    Returns
    -------
    float
        Angle in degrees in the range [0, 180].
    """
    # Clamp z/g to [-1, 1] to guard against rounding noise beyond ±g
    ratio = max(-1.0, min(1.0, z / g))
    # acos returns 0 when z == +g (face-up) and π when z == -g (upside-down)
    raw_angle = degrees(acos(ratio))
    # Remap: upside-down (raw=180°) → 0°, perpendicular (raw=90°) → 90°
    return 180.0 - raw_angle
