from db import get_db

def get_all_items():
    conn = get_db()
    cur = conn.cursor()

    try:
        # Step 1: Call stored procedure (returns cursor name)
        cur.callproc("hotel_master.get_all_item")

        # The function returns a tuple with cursor name
        result = cur.fetchone()
        cursor_name = result[0]

        # Step 2: Fetch all rows from the cursor
        cur.execute(f"FETCH ALL FROM {cursor_name};")
        items = cur.fetchall()

        # Step 3: Close cursor
        cur.execute(f"CLOSE {cursor_name};")

        return items

    finally:
        cur.close()
        conn.close()
        
        
        
def add_item(item_name, item_code, category, description, purchase_price, selling_price, unit, gst_percentage, stockable):
    conn = get_db()
    cur = conn.cursor()

    cur.callproc("hotel_master.sp_add_item", (
        item_name,
        item_code,
        category,
        description,
        purchase_price,
        selling_price,
        unit,
        gst_percentage,
        stockable
    ))

    conn.commit()
    cur.close()
    conn.close()
    

def update_item(item_id, item_name, item_code, category, description,
                purchase_price, selling_price, unit, gst_percentage, stockable):

    conn = get_db()
    cur = conn.cursor()

    cur.callproc("hotel_master.sp_update_item", (
        item_id,
        item_name,
        item_code,
        category,
        description,
        purchase_price,
        selling_price,
        unit,
        gst_percentage,
        stockable
    ))

    conn.commit()
    cur.close()
    conn.close()
