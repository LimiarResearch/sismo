"""The detector: for a set of fields observed over time, it says which field left its normal (where), since when (when) and how (up
or down, by how many standard deviations of the field's own normal, and the trajectory). Given the response of a model, it separates
a relation that broke (alert) from an input that changed (log)."""
from .decision import Decision
from .reference import Detector
from .trajectory import Trajectories
from .monitor import Monitor, declared_scale
