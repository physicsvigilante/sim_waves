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


class ResourceLimitError(BaseException):
    """The request ran out of its time or memory limit (m15a). It says nothing about the
    physics: it is not a SceneError, and derives from BaseException so that no
    `except Exception` can turn it into a fallback, a refusal or an inconsistency."""

    def __init__(self, kind, limit, detail=""):
        self.kind, self.limit, self.detail = kind, limit, detail
        super().__init__(f"RESOURCE LIMIT ({kind} {limit})" + (f": {detail}" if detail else ""))
