"""Every failure the engine reports. The engine never guesses: it raises one of these."""


class SceneError(Exception):
    """The scene is malformed or uses something the engine does not support."""


class InconsistentError(SceneError):
    """The scene's facts contradict each other; no physical situation satisfies them."""


class AmbiguousError(SceneError):
    """The scene's facts allow more than one situation; an explicit assumption is needed."""


class PhysicalRangeError(SceneError):
    """A value is outside the physical range of its kind (a gas or fluid speed in light's
    range). In a sampled check, a scaled run that raises this left the physics: it is
    skipped, and the basis says so."""


class UndeterminedError(SceneError):
    """A requested quantity depends on something the scene never fixed."""
