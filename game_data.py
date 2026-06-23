import psycopg
from psycopg.rows import dict_row


def get_connection():
    return psycopg.connect("dbname=wcprediction_development", row_factory=dict_row)


def matches_for_team(code: str) -> list[dict]:
    sql = """
        SELECT m.kick_off, m.stage, m.venue,
               t1.code AS team_1, t2.code AS team_2,
               m.team_1_goals, m.team_2_goals
        FROM matches m
        JOIN teams t1 ON t1.id = m.team_1_id
        JOIN teams t2 ON t2.id = m.team_2_id
        WHERE t1.code = %(code)s OR t2.code = %(code)s
        ORDER BY m.kick_off
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, {"code": code.upper()})
            rows = cur.fetchall()
    
    for row in rows:
        row['kick_off'] = row['kick_off'].isoformat()

    return rows