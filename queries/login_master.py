from db import get_db

# ---------------- LOGIN ----------------
def validate_user(username, password):
    conn = get_db()
    cur = conn.cursor()

    # returns boolean from sp_login
    cur.callproc("login_master.sp_login", (username, password))
    result = cur.fetchone()[0]

    cur.close()
    conn.close()

    return result  # True / False


#-------------------- Get All UserWarning

def get_user_details(username):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.id, u.username, r.role_name
        FROM login_master.users u join login_master.roles r
        on u.role_id = r.id
        WHERE username = %s
    """, (username,))

    user = cur.fetchone()

    cur.close()
    conn.close()
    return user



# ------------- UPDATE PASSWORD -------------
def update_user_password(username, new_password):
    conn = get_db()
    cur = conn.cursor()

    cur.callproc("login_master.sp_update_password", (username, new_password))
    conn.commit()

    cur.close()
    conn.close()


# --------------- ADD USER ----------------
def add_user(username, password, role_id, email):
    conn = get_db()
    cur = conn.cursor()

    cur.callproc("login_master.sp_add_user", (username, password, role_id, email))
    conn.commit()

    cur.close()
    conn.close()


# --------------- ACTIVATE / DEACTIVATE USER ----------------
def update_user_status(username, is_active):
    conn = get_db()
    cur = conn.cursor()

    cur.callproc("login_master.sp_update_user", (username, is_active))
    conn.commit()

    cur.close()
    conn.close()


#-------------- ll user 
def get_all_users():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.id, u.username, r.role_name, u.email, u.is_active
        FROM login_master.users u
        JOIN login_master.roles r ON u.role_id = r.id
        ORDER BY u.id
    """)

    users = cur.fetchall()

    cur.close()
    conn.close()
    return users

#-------------------------Eidt
