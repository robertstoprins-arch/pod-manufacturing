import os, psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='pod_specs' ORDER BY ordinal_position")
print("pod_specs columns:", [r[0] for r in cur.fetchall()])
cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='build_ups' ORDER BY ordinal_position")
print("build_ups columns:", [r[0] for r in cur.fetchall()])
conn.close()
