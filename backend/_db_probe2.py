import pymysql

cfg_scm = dict(
    host="192.168.0.75", port=3306, user="wecon_scm_20251228",
    password="eFnSMdwFBGJF3DrK", database="wecon_scm_20251228", charset="utf8mb4",
)
cfg_anl = dict(
    host="192.168.0.75", port=3306, user="wecon_analyze",
    password="bBfN2kPAnx7myhXs", database="wecon_analyze", charset="utf8mb4",
)


def desc_table(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"DESCRIBE `{table}`")
        rows = cur.fetchall()
    print(f"--- {table} ({len(rows)} cols) ---")
    for r in rows:
        print(f"  {str(r[0]):40s} {str(r[1]):25s} null={r[2]} key={r[3]}")


def count_rows(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(1) FROM `{table}`")
        return cur.fetchone()[0]


def sample_row(conn, table):
    with conn.cursor() as cur:
        cur.execute(f"SELECT * FROM `{table}` LIMIT 1")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    print(f"--- {table} sample ---")
    if rows:
        for col, val in zip(cols, rows[0]):
            print(f"  {col:40s} = {val!r}")


def distinct_values(conn, table, col, limit=20):
    with conn.cursor() as cur:
        cur.execute(f"SELECT DISTINCT `{col}` FROM `{table}` WHERE `{col}` IS NOT NULL LIMIT {limit}")
        return [r[0] for r in cur.fetchall()]


print("##### ANALYSIS: targeting tables #####")
c2 = pymysql.connect(**cfg_anl)
for t in ["bi_analyze_ad_targeting", "bi_analyze_ad_targeting_realtime",
          "bi_analyze_ad_group", "bi_analyze_ad_group_realtime"]:
    try:
        desc_table(c2, t)
        print(f"  rows={count_rows(c2, t)}")
        sample_row(c2, t)
        print()
    except Exception as e:
        print(f"  ERR {t}: {e}")

print("##### ANALYSIS: targeting type/match distinct values #####")
for t, col in [("bi_analyze_ad_targeting", "targeting_type"),
               ("bi_analyze_ad_targeting", "targeting_match"),
               ("bi_analyze_ad_targeting_realtime", "targeting_type"),
               ("bi_analyze_ad_targeting_realtime", "targeting_match")]:
    try:
        vals = distinct_values(c2, t, col)
        print(f"  {t}.{col} = {vals}")
    except Exception as e:
        print(f"  ERR {t}.{col}: {e}")

print()
print("##### ANALYSIS: ad_group group_id/group_code coverage #####")
with c2.cursor() as cur:
    cur.execute("SELECT COUNT(DISTINCT group_id), COUNT(DISTINCT group_code) FROM bi_analyze_ad_targeting WHERE group_id IS NOT NULL OR group_code IS NOT NULL")
    print(f"  targeting group_id/group_code distinct: {cur.fetchone()}")
    cur.execute("SELECT COUNT(DISTINCT campaign_code) FROM bi_analyze_ad_targeting")
    print(f"  targeting campaign_code distinct: {cur.fetchone()}")
c2.close()

print()
print("##### SCM: ad_group / targeting tables #####")
c1 = pymysql.connect(**cfg_scm)
for t in ["eb_ad_group", "eb_ad_targeting", "eb_ad_negative_targeting", "eb_ad_product"]:
    try:
        desc_table(c1, t)
        print(f"  rows={count_rows(c1, t)}")
        sample_row(c1, t)
        print()
    except Exception as e:
        print(f"  ERR {t}: {e}")
c1.close()