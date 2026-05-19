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
