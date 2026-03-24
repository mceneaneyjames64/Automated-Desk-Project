from math import atan2, degrees

def vector_to_degrees(x, y):
	"""convert coordinates into an angle in degrees"""
    angle = degrees(atan2(y, x))
    if angle <0:
	    angle += 360
    return angle
