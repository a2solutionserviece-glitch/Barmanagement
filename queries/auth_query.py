from db import get_db

def validate_user(username, password):
    conn = get_db()
    cur = conn.cursor()

    # Call stored procedure instead of direct SELECT query
    cur.callproc("sp_validate_user", (username,))

    user = cur.fetchone()

    cur.close()
    conn.close()

    return user
