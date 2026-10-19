from marc_comparator.comparators import BaseComparator

from adapters.database import DatabaseSession
from entities.settings import Settings, SettingsScope

from . import UsedComparatorClass, UsedComparatorConfig
from .models import ComparisonSettings


def load_gate_comparator(db_session: DatabaseSession) -> tuple[BaseComparator | None, bool]:
    """The comparator a linker should rank candidates with, and whether its
    verdict is the one the pipeline would reach.

    A linker builds its own comparator otherwise, on whatever scale that
    class defaults to, which makes its ``minimum_confidence`` mean something
    different from the score an operator is shown. It gets the configured one
    instead — with one exception: the gate runs per candidate, several times
    per record, and cannot call an LLM however the comparison feature is set
    up. When the LLM is off the two are the same comparator and the gate's
    result is the pipeline's; when it is on they are not, and the pipeline
    has to reach its own verdict.
    """

    settings = Settings.get(db_session, SettingsScope.Comparison, ComparisonSettings)
    if not settings:
        return None, False
    config = (settings.comparator or UsedComparatorConfig()).model_copy(
        update={"llm_enabled": False, "nonstandard_llm_enabled": False}
    )
    stored = settings.comparator or UsedComparatorConfig()
    equivalent = not stored.llm_enabled and not stored.nonstandard_llm_enabled
    try:
        return UsedComparatorClass(config), equivalent
    except ValueError:
        return None, False
