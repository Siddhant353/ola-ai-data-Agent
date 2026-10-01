from sql_guard import check_select_only

ALLOWED = [
    "SELECT * FROM users LIMIT 10;",
    "select payment_method, count(*) from payments group by 1",
    "WITH t AS (SELECT 1) SELECT * FROM t",
    "SELECT created_at, updated_at FROM rides -- latest rides",
    "SELECT 1 -- delete me",
]
BLOCKED = [
    "DELETE FROM payments",
    "SELECT 1; DROP TABLE users",
    "WITH x AS (DELETE FROM payments RETURNING *) SELECT * FROM x",
    "SELECT * INTO backup FROM users",
    "UPDATE users SET is_active = false",
    "/* harmless */ DROP TABLE users",
    "",
]

failures = 0
for sql in ALLOWED:
    ok, reason = check_select_only(sql)
    print("PASS" if ok else "FAIL", "| should allow |", sql or "<empty>", "|", reason)
    failures += not ok
for sql in BLOCKED:
    ok, reason = check_select_only(sql)
    print("PASS" if not ok else "FAIL", "| should block |", sql or "<empty>", "|", reason)
    failures += ok

print(f"\n{failures} failure(s)")
raise SystemExit(1 if failures else 0)
