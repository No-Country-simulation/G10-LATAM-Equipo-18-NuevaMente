import sqlite3
import os

db_paths = [
    "/app/users.db",
    "users.db",
    "/home/ubuntu/app/backend/users.db"
]

def check():
    for p in db_paths:
        if os.path.exists(p):
            print(f"=== DB found at: {p} ===")
            conn = sqlite3.connect(p)
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in c.fetchall()]
            print("Tables:", tables)
            for t in tables:
                c.execute(f"SELECT count(*) FROM {t}")
                cnt = c.fetchone()[0]
                print(f"  - {t}: {cnt} rows")
            if "documentos" in tables:
                c.execute("SELECT id, user_id, title, object_key FROM documentos")
                print("Documentos rows:", c.fetchall())
            if "contenidos" in tables:
                c.execute("SELECT id, user_id, title, object_key_json FROM contenidos")
                print("Contenidos rows:", c.fetchall())
            conn.close()

if __name__ == "__main__":
    check()
