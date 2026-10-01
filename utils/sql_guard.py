import re

# Keywords that change data, structure or permissions. A read-only question never needs them.
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|execute|merge|vacuum|reindex|into)\b",
    re.IGNORECASE,
)


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)  # block comments
    sql = re.sub(r"--[^\n]*", " ", sql)                     # line comments
    return sql


def check_select_only(sql_query: str) -> tuple[bool, str]:
    """Return (is_allowed, reason). Allows exactly one SELECT (or WITH ... SELECT) statement."""
    if not sql_query or not sql_query.strip():
        return False, "The generated query is empty."

    cleaned = _strip_comments(sql_query).strip().rstrip(";").strip()

    if ";" in cleaned:
        return False, "Multiple SQL statements are not allowed."
    if not re.match(r"^(select|with)\b", cleaned, flags=re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    match = FORBIDDEN.search(cleaned)
    if match:
        return False, f"The query contains the forbidden keyword {match.group(0).upper()}."

    return True, "The query is a single read-only SELECT."
