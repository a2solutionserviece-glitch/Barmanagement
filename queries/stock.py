from db import get_db



def add_stock(item_id, quantity, notes):
    conn = get_db()
    cur = conn.cursor()
    cur.callproc("hotel_master.sp_add_stock", (item_id, quantity, notes))
    conn.commit()
    cur.close()
    conn.close()


def reduce_stock(item_id, quantity, notes):
    conn = get_db()
    cur = conn.cursor()
    cur.callproc("hotel_master.sp_reduce_stock", (item_id, quantity, notes))
    conn.commit()
    cur.close()
    conn.close()


def update_stock(trans_id, quantity, notes):
    conn = get_db()
    cur = conn.cursor()
    cur.callproc("hotel_master.sp_update_stock", (trans_id, quantity, notes))
    conn.commit()
    cur.close()
    conn.close()

def get_stock_history(item_id):
    conn = get_db()
    cur = conn.cursor()

    cur.callproc("hotel_master.sp_stock_history", (item_id,))
    cursor_name = cur.fetchone()[0]

    cur.execute(f"FETCH ALL FROM {cursor_name}")
    history = cur.fetchall()

    cur.execute(f"CLOSE {cursor_name}")
    conn.close()

    return history

def get_stock_balance(item_id):
    conn = get_db()
    cur = conn.cursor()
    cur.callproc("hotel_master.sp_get_stock_balance", (item_id,))
    balance = cur.fetchone()[0]
    cur.close()
    conn.close()
    return balance
