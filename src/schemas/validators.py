class Validators:

    @staticmethod
    def password(v: str | None, *, optional: bool = False) -> str | None:
        if v is None:
            if optional:
                return v 
            raise ValueError("Password is required")
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_symbol = any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in v)
        if not (has_letter and has_digit and has_symbol):
            raise ValueError("Password must contain letter, number and symbol")
        return v
