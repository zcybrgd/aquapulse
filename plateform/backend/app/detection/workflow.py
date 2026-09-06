"""Detection investigation transition table. No I/O."""

ACTION_MAP: dict[str, tuple[str, ...]] = {
    "new": ("start_review", "add_note", "dismiss", "merge"),
    "queued": ("start_review", "add_note", "dismiss", "merge"),
    "under_review": ("add_note", "dismiss", "merge", "promote"),
    "dismissed": ("add_note", "reopen"),
    "promoted": (),
    "merged": (),
}

ACTIVE_STATUSES = {"new", "queued", "under_review"}
TERMINAL_STATUSES = {"promoted", "merged"}
NOTE_STATUSES = {"new", "queued", "under_review", "dismissed"}
START_REVIEW_STATUSES = {"new", "queued"}
DISMISS_STATUSES = {"new", "queued", "under_review"}
MERGE_STATUSES = {"new", "queued", "under_review"}


def allowed_actions(status: str) -> list[str]:
    return list(ACTION_MAP.get(status, ()))
