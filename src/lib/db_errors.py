from sqlalchemy.exc import IntegrityError


def is_unique_violation(e: IntegrityError) -> bool:
    orig = e.orig
    if orig.__class__.__name__ == "UniqueViolationError":
        return True
    if getattr(orig, "args", None) and orig.args[0] == 1062:
        return True
    return "unique" in str(orig).lower()


def is_fk_violation(e: IntegrityError) -> bool:
    orig = e.orig
    if orig.__class__.__name__ == "ForeignKeyViolationError":
        return True
    if getattr(orig, "args", None) and orig.args[0] in (1452, 1451):
        return True
    return "foreign key" in str(orig).lower()


def is_check_violation(e: IntegrityError, name: str | None = None) -> bool:
    orig = e.orig
    if orig.__class__.__name__ == "CheckViolationError":
        matched = True
    elif getattr(orig, "args", None) and orig.args[0] == 3819:
        matched = True
    else:
        matched = "check constraint" in str(orig).lower()
    if not matched:
        return False
    if name is None:
        return True
    return name.lower() in str(orig).lower()
