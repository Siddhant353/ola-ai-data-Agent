import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.environ["host"],
    port=int(os.environ["port"]),
    database=os.environ["database"],
    user=os.environ["readonly_user"],
    password=os.environ["readonly_password"],
)
cur = conn.cursor()

cur.execute("SELECT count(*) FROM payments")
print("READ works:", cur.fetchone())
conn.rollback()  # end the read transaction so each test below starts a fresh one

for statement in ["DELETE FROM payments", "CREATE TABLE ola_write_test (id int)", "DROP TABLE payments"]:
    try:
        cur.execute("SET TRANSACTION READ WRITE")  # try to switch off the soft read-only guard first
        cur.execute(statement)
        print("!! NOT BLOCKED:", statement)
    except Exception as e:
        print("blocked:", statement, "->", type(e).__name__)
    finally:
        conn.rollback()  # nothing is ever kept, even if a statement somehow worked
conn.close()