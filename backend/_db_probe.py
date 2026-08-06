import pymysql

cfg_scm = dict(
    host="192.168.0.75",
    port=3306,
    user="wecon_scm_20251228",
    password="eFnSMdwFBGJF3DrK",
    database="wecon_scm_20251228",
    charset="utf8mb4",
)
cfg_anl = dict(
    host="192.168.0.75",
    port=3306,
    user="wecon_analyze",
    password="bBfN2kPAnx7myhXs",
    database="wecon_analyze",
    charset="utf8mb4",
)


def show_tables(conn, label):
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        tables = [r[0] for r in cur.fetchall()]
    print(f"=== {label} tables ({len(tables)}) ===")
    for t in tables:
        print(" ", t)


def desc_table(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"DESCRIBE `{table}`")
        rows = cur.fetchall()
    print(f"--- {table} ({len(rows)} cols) ---")
    for r in rows:
        print(f"  {str(r[0]):35s} {str(r[1]):25s} null={r[2]} key={r[3]} default={r[4]}")


def sample_row(conn, table, limit=1):
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM `{table}` LIMIT {limit}")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    print(f"--- {table} sample ({len(rows)} rows) ---")
    if rows:
        for col, val in zip(cols, rows[0]):
            print(f"  {col:35s} = {val!r}")


def count_rows(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(1) FROM `{table}`")
        return cur.fetchone()[0]


print("##### SCM DATABASE #####")
c1 = pymysql.connect(**cfg_scm)
show_tables(c1, "SCM")
for t in ["eb_ad_campaign"]:
    try:
        desc_table(c1, t)
        print(f"  rows={count_rows(c1, t)}")
        sample_row(c1, t)
    except Exception as e:
        print(f"  ERR {t}: {e}")
c1.close()

print()
print("##### ANALYSIS DATABASE #####")
c2 = pymysql.connect(**cfg_anl)
show_tables(c2, "ANALYSIS")
for t in [
    "bi_analyze_ad_campaign",
    "bi_analyze_ad_campaign_realtime",
    "bi_analyze_ad_targeting",
    "bi_analyze_ad_targeting_realtime",
]:
    try:
        desc_table(c2, t)
        print(f"  rows={count_rows(c2, t)}")
        sample_row(c2, t)
    except Exception as e:
        print(f"  ERR {t}: {e}")
c2.close()