from flask import Flask, render_template, request, redirect, session, flash,jsonify, send_file
import webbrowser
from db import get_db
import threading,json
from queries.login_master import validate_user, update_user_password, add_user, update_user_status, get_user_details ,get_all_users
from queries.items import get_all_items,add_item,update_item
#from queries.order_master import get_tables
from queries.stock import get_stock_history,add_stock,reduce_stock,update_stock,get_stock_balance

app = Flask(__name__)
app.secret_key = "asif_bar_app"


# ------------------ LOGIN ----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Call stored procedure: returns True/False
        is_valid = validate_user(username, password)

        if is_valid:
            # Fetch user details from database
            user = get_user_details(username)

            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[2]

            return redirect("/")
        else:
            flash("Invalid Username or Password", "danger")

    return render_template("login.html")



# ------------------ LOGOUT ----------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")



# ------------------ HOME PAGE ----------------------
@app.route("/")


@app.route("/dashboard")
def get_dash():
   
    return render_template("dashboard.html")

@app.route("/api/dashboard")
def api_dashboard():
    conn = get_db()
    cur = conn.cursor()
    
    
       # Load threshold from hotel_settings (only row = 1)
    cur.execute("""
        SELECT lowstockthreshold
        FROM hotel_master.hotel_settings
        LIMIT 1
    """)
    setting_row = cur.fetchone()

    low_threshold = setting_row[0] if setting_row else 5   # default 5
 
    # Today range
    cur.execute("""
        SELECT 
            COALESCE(SUM(total_amount),0) AS sales,
            COUNT(*) AS orders
        FROM hotel_order.order_header
        WHERE DATE(created_at) = CURRENT_DATE
    """)
    s = cur.fetchone()
    today_sales = float(s[0])
    today_orders = s[1]

    # Items sold today
    cur.execute("""
        SELECT COALESCE(SUM(qty),0)
        FROM hotel_order.order_details od
        JOIN hotel_order.order_header oh ON oh.order_id = od.order_id
        WHERE DATE(oh.created_at) = CURRENT_DATE
    """)
    today_items = cur.fetchone()[0]

    # Low stock
    cur.execute("""
        SELECT count(*)
        FROM hotel_master.Stock_master s
        join hotel_master.item_master im 
        on s.item_id = im.id
        WHERE current_stock <=%s
        and im.stockable = true    
    """, (low_threshold,))
    low_stock_count = cur.fetchone()[0]

    # Low stock list
    cur.execute("""
        SELECT i.item_name, s.current_stock AS qty
        FROM hotel_master.Stock_master s
        join hotel_master.item_master i 
        on s.item_id = i.id
        WHERE current_stock <= %s
         and stockable = true
        ORDER BY qty ASC
        LIMIT 10
    """, (low_threshold,))
    low_stock_list = [dict(item_name=r[0], qty=r[1]) for r in cur.fetchall()]

    # Top items (last 7 days)
    cur.execute("""
        SELECT im.item_name, SUM(od.qty) AS sold
        FROM hotel_order.order_details od
        JOIN hotel_master.item_master im ON im.id = od.item_id
        JOIN hotel_order.order_header oh ON oh.order_id = od.order_id
        WHERE oh.created_at >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY im.item_name
        ORDER BY sold DESC
        LIMIT 10
    """)
    top_selling = [dict(item_name=r[0], sold=r[1]) for r in cur.fetchall()]

    # Recent orders
    cur.execute("""
        SELECT order_id, total_amount
        FROM hotel_order.order_header
        ORDER BY created_at DESC
        LIMIT 10
    """)
    recent_orders = [dict(order_id=r[0], amount=float(r[1])) for r in cur.fetchall()]

    # 7-day sales chart
    cur.execute("""
        SELECT TO_CHAR(created_at, 'DD Mon') AS d, SUM(total_amount)
        FROM hotel_order.order_header
        WHERE created_at >= CURRENT_DATE - INTERVAL '6 days'
        GROUP BY d
        ORDER BY MIN(created_at)
    """)
    rows = cur.fetchall()

    labels = [r[0] for r in rows]
    values = [float(r[1]) for r in rows]

    return jsonify({
        "today_sales": today_sales,
        "today_orders": today_orders,
        "today_items_sold": today_items,
        "low_stock_count": low_stock_count,
        "low_stock_list": low_stock_list,
        "top_selling": top_selling,
        "recent_orders": recent_orders,
        "sales_7_days": {
            "labels": labels,
            "values": values
        }
    })


#--------------------UserPage


@app.route("/users")
def users():
    if "username" not in session:
        return redirect("/login")

    # Only Admins allowed
    if session["role"] != "admin" and session["role"] != 1:
        flash("Access Denied!", "danger")
        return redirect("/dashboard")

    # Load all users from DB
    users = get_all_users()

    return render_template("users.html", users=users)



#------------------- Add USERS

@app.route("/add_user", methods=["POST"])
def add_user_route():
    username = request.form["username"]
    password = request.form["password"]
    role_id = request.form["role_id"]
    email = request.form["email"]

    add_user(username, password, role_id, email)
    flash("User Added Successfully!", "success")
    return redirect("/users")



# ------------------ ACTIVATE / DEACTIVATE USER ----------------------

@app.route("/toggle_user/<username>")
def update_status(username):

    conn = get_db()
    cur = conn.cursor()

    # Read current active status
    cur.execute("SELECT is_active FROM login_master.users WHERE username = %s", (username,))
    current_status = cur.fetchone()

    if current_status is None:
        flash("User not found!", "danger")
        return redirect("/users")

    # Toggle status
    new_status = not current_status[0]

    # Call your stored procedure
    update_user_status(username, new_status)

    flash("User status updated!", "success")
    return redirect("/users")


#--------------- EDIT USER and Update


@app.route("/edit_user/<username>")
def edit_user(username):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT u.username, u.email, u.role_id, r.role_name ,u.password
        FROM login_master.users u
        JOIN login_master.roles r ON u.role_id = r.id
        WHERE u.username = %s
    """, (username,))

    user = cur.fetchone()

    cur.close()
    conn.close()

    if not user:
        flash("User not found!", "danger")
        return redirect("/users")

    return render_template("edit_user.html", user=user)

@app.route("/update_user", methods=["POST"])
def update_user():
    old_username = request.form["old_username"]
    new_username = request.form["username"]
    email = request.form["email"]
    role_id = request.form["role_id"]
    password = request.form["password"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE login_master.users
        SET email = %s, role_id = %s , password = %s ,username = %s
        WHERE username = %s
    """, (email, role_id, password, new_username, old_username))

    conn.commit()
    cur.close()
    conn.close()

    flash("User updated successfully!", "success")
    return redirect("/users")
#---------------------------------

#----------------- DELETE USER

@app.route("/delete_user/<username>")
def delete_user(username):
    conn = get_db()
    cur = conn.cursor()

    # Check if user exists
    cur.execute("SELECT username FROM login_master.users WHERE username = %s", (username,))
    user = cur.fetchone()

    if not user:
        flash("User not found!", "danger")
        return redirect("/users")

    # Delete user
    cur.execute("DELETE FROM login_master.users WHERE username = %s", (username,))
    conn.commit()

    cur.close()
    conn.close()

    flash("User deleted successfully!", "success")
    return redirect("/users")
    
    
#----------------Item Master------------------

@app.route("/item_master")
def item_master():
    items = get_all_items()
    return render_template("item_master.html", items=items)


#----------------  ADD ITEM 

@app.route("/add_item", methods=["POST"])
def add_item_route():
    item_name = request.form["item_name"]
    item_code = request.form["item_code"]
    category = request.form["category"]
    description = request.form["description"]
    purchase_price = request.form["purchase_price"]
    selling_price = request.form["selling_price"]
    unit = request.form["unit"]
    gst_percentage = request.form["gst_percentage"]
    stockable = request.form["stockable"] == "true"

    add_item(
        item_name,
        item_code,
        category,
        description,
        purchase_price,
        selling_price,
        unit,
        gst_percentage,
        stockable
    )

    flash("Item added successfully!", "success")
    return redirect("/item_master")

#--------------------------Update_item
@app.route("/edit_item/<int:item_id>")
def edit_item(item_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, item_name, item_code, category, description,
               purchase_price, selling_price, unit, gst_percentage,
               stockable
        FROM hotel_master.item_master
        WHERE id = %s
    """, (item_id,))

    item = cur.fetchone()

    cur.close()
    conn.close()

    if not item:
        return {"error": "Item not found"}, 404

    return {
        "id": item[0],
        "item_name": item[1],
        "item_code": item[2],
        "category": item[3],
        "description": item[4],
        "purchase_price": float(item[5]),
        "selling_price": float(item[6]),
        "unit": item[7],
        "gst_percentage": float(item[8]),
        "stockable": item[9]
    }

@app.route("/update_item", methods=["POST"])
def update_item_route():
    # Read form fields from the Edit Item popup modal
    item_id = request.form["item_id"]
    item_name = request.form["item_name"]
    item_code = request.form["item_code"]
    category = request.form["category"]
    description = request.form["description"]
    purchase_price = request.form["purchase_price"]
    selling_price = request.form["selling_price"]
    unit = request.form["unit"]
    gst_percentage = request.form["gst_percentage"]
    stockable = request.form["stockable"] == "true"

    # Call backend function that executes sp_update_item
    update_item(
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
    )

    flash("Item updated successfully!", "success")
    return redirect("/item_master")

#------------- DELETE Item

@app.route("/delete_item/<int:item_id>")
def delete_item(item_id):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM hotel_master.item_master
        WHERE id = %s
    """, (item_id,))

    conn.commit()
    cur.close()
    conn.close()

    flash("Item deleted successfully!", "success")
    return redirect("/item_master")



# --------------- stock Master------------------
@app.route("/stock_master")
def stock_master():

    # 1. Load all items for dropdown
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, item_name, unit 
        FROM hotel_master.item_master
        WHERE is_active = TRUE
        and stockable = TRUE
        ORDER BY item_name
    """)
    items = cur.fetchall()

    # 2. Load stock balances
    stocks = []
    for item in items:
        item_id = item[0]

        # call procedure to get current stock
        cur.callproc("hotel_master.sp_get_stock_balance", (item_id,))
        balance = cur.fetchone()[0]

        # Last movement date
        cur.execute("""
            SELECT created_at
            FROM hotel_master.stock_transactions
            WHERE item_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, (item_id,))
        last = cur.fetchone()
        last_date = last[0] if last else "—"

        stocks.append({
            "id": item_id,
            "item_name": item[1],
            "unit": item[2],
            "current_stock": balance,
            "updated_at": last_date
        })

    cur.close()
    conn.close()

    return render_template(
        "stock_master.html",
        items=items,
        stocks=stocks
    )




@app.route("/add_stock", methods=["POST"])
def add_stock_route():
    item_id = request.form["item_id"]
    quantity = request.form["quantity"]
    notes = request.form["notes"]
    add_stock(item_id, quantity, notes)
    flash("Stock added successfully!", "success")
    return redirect("/stock_master")


@app.route("/reduce_stock", methods=["POST"])
def reduce_stock_route():
    item_id = request.form["item_id"]
    quantity = request.form["quantity"]
    notes = request.form["notes"]
    reduce_stock(item_id, quantity, notes)
    flash("Stock reduced!", "success")
    return redirect("/stock_master")

@app.route("/stock_history/<int:item_id>")
def stock_history_route(item_id):
    history = get_stock_history(item_id)
    return render_template("stock_history.html", history=history)

@app.route("/update_stock", methods=["POST"])
def update_stock_route():
    item_id = request.form["trans_id"]   # actually item id
    quantity = request.form["quantity"]
    notes = request.form["notes"]

    # convert update to:
    # OUT old stock
    # IN new stock

    current_stock = get_stock_balance(item_id)

    reduce_stock(item_id, current_stock, "Auto Adjust Before Update")
    add_stock(item_id, quantity, notes)

    flash("Stock updated!", "success")
    return redirect("/stock_master")



# ----------------order master


#item master called to get item list 
@app.route("/api/items")
def api_get_items():
    conn = get_db()
    cur = conn.cursor()

    # MUST pass empty tuple when no arguments exist
    cur.execute("""
         SELECT i.id, item_name, selling_price,unit ,st.current_stock as quantity ,is_active
        FROM hotel_master.item_master i
        left join hotel_master.stock_master st 
        on i.id  = st.item_id
        WHERE is_active = TRUE
        ORDER BY item_name
    """)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    items = [
        {
            "id": r[0],
            "item_name": r[1],
            "selling_price": float(r[2]),
            "unit": r[3],
            "quantity": r[4],
            "is_active": r[5]
        }
        for r in rows
    ]

    return jsonify(items)

@app.route("/api/get_running_order/<int:table_id>")
def get_running_order(table_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT oh.order_id
            FROM hotel_order.order_header oh
            WHERE oh.table_id = %s AND oh.order_status = 'RUNNING'
            ORDER BY oh.order_id DESC
            LIMIT 1
        """, (table_id,))
        
        row = cur.fetchone()
        if not row:
            return jsonify({"ok": True, "order_id": None, "items": []})

        order_id = row[0]

        cur.execute("""
            SELECT od.item_id, im.item_name, im.unit, sum(od.qty), od.price
            FROM hotel_order.order_details od
            JOIN hotel_master.item_master im ON im.id = od.item_id
            WHERE od.order_id = %s
            group by od.item_id, im.item_name, im.unit,od.price
        """, (order_id,))

        items = []
        for r in cur.fetchall():
            items.append({
                "item_id": r[0],
                "item_name": r[1],
                "unit": r[2],
                "qty": r[3],
                "price": float(r[4])
            })

        return jsonify({"ok": True, "order_id": order_id, "items": items})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

    finally:
        cur.close()
        conn.close()

    
@app.route("/save_order", methods=["POST"])
def save_order():
    data = request.get_json()

    table_id = int(data["table_id"])
    table_no = int(data["table_no"])       # Added (previously missing)
    items = data["items"]

    conn = get_db()
    cur = conn.cursor()

    try:
        # Call the single stored procedure that creates/updates the running order
        cur.execute("""
            SELECT hotel_order.save_running_order(%s, %s, %s::json)
        """, (table_id, table_no, json.dumps(items)))

        order_id = cur.fetchone()[0]
        
        conn.commit()

    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

    finally:
        cur.close()
        conn.close()

    return jsonify({"ok": True, "order_id": order_id})


#------------- DELETE Item From Cart 

@app.route("/api/delete_order_item", methods=["POST"])
def delete_order_item():
    data = request.get_json()
    order_id = data["order_id"]
    item_id = data["item_id"]

    conn = get_db()
    cur = conn.cursor()
    
    #print("Executing SQL:",
      #f"DELETE FROM hotel_order.order_details WHERE order_id = {order_id}")

    try:
        cur.execute("""
            DELETE FROM hotel_order.order_details
            WHERE order_id = %s AND item_id = %s
        """, (order_id, item_id))

        # Update total in order_header
        cur.execute("""
            UPDATE hotel_order.order_header
            SET total_amount = (
                SELECT COALESCE(SUM(qty * price), 0)
                FROM hotel_order.order_details
                WHERE order_id = %s
            ),
            updated_at = NOW()
            WHERE order_id = %s
        """, (order_id, order_id))

        conn.commit()
        return jsonify({"ok": True})

    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)})

    finally:
        cur.close()
        conn.close()

#--------- Logo


@app.route("/invoice_logo")
def invoice_logo():
    return send_file("static/logo.png", mimetype="image/png")



#------------ genrate Invoice 
@app.route("/invoice/<int:order_id>")
def invoice(order_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        # ---- FETCH ORDER HEADER ----
        cur.execute("""
            SELECT order_id, table_id, table_no, total_amount, created_at
            FROM hotel_order.order_header
            WHERE order_id = %s
        """, (order_id,))
        row = cur.fetchone()

        if not row:
            return "Order not found", 404

        order = {
            "order_id": row[0],
            "table_id": row[1],
            "table_no": row[2],
            "total_amount": float(row[3]),
            "datetime": row[4].strftime("%d-%m-%Y %H:%M:%S")
        }

        # ---- FETCH ORDER ITEMS ----
        cur.execute("""
            SELECT od.item_id, im.item_name, im.unit, od.qty, od.price
            FROM hotel_order.order_details od
            JOIN hotel_master.item_master im ON im.id = od.item_id
            WHERE od.order_id = %s
        """, (order_id,))

        items = []
        for r in cur.fetchall():
            items.append({
                "item_id": r[0],
                "item_name": r[1],
                "unit": r[2],
                "qty": r[3],
                "price": float(r[4])
            })

        # ---- FETCH HOTEL SETTINGS ----
        cur.execute("""
            SELECT json_build_object(
                'hotelName', hotelname,
                'shortName', shortname,
                'addressLine1', addressline1,
                'addressLine2', addressline2,
                'city', city,
                'state', state,
                'pincode', pincode,
                'phone', phone,
                'email', email,
                'gstNumber', gstnumber,
                'panNumber', pannumber,
                'printHeader', printheader,
                'printFooter', printfooter
            )
            FROM hotel_master.hotel_settings
            LIMIT 1;
        """)

        r = cur.fetchone()
        settings = r[0] if r and r[0] else {
            "hotelName": "",
            "shortName": "",
            "addressLine1": "",
            "addressLine2": "",
            "city": "",
            "state": "",
            "pincode": "",
            "phone": "",
            "email": "",
            "gstNumber": "",
            "panNumber": "",
            "printHeader": "",
            "printFooter": ""
        }

        # ---- RENDER TEMPLATE ----
        return render_template("invoice.html",
                               order=order,
                               items=items,
                               settings=settings)

    finally:
        cur.close()
        conn.close()



@app.route("/close_order/<int:order_id>", methods=["POST"])
def close_order(order_id):
    conn = get_db()
    cur = conn.cursor()

    try:
        cur.execute("SELECT hotel_order.close_order(%s)", (order_id,))
        conn.commit()
        return jsonify({"ok": True})

    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "error": str(e)})

    finally:
        cur.close()
        conn.close()

@app.route("/order_master")
def order_master():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            t.id,
            t.table_no,
            t.description,
            t.status,
            oh.order_id,
            oh.total_amount
        FROM hotel_order.table_master t
        LEFT JOIN hotel_order.order_header oh 
            ON oh.table_id = t.id 
            AND oh.order_status = 'RUNNING'
        ORDER BY t.table_no
    """)

    tables = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("order_master.html", tables=tables)


# ---------------- Settings

@app.route("/setting", methods=["GET"])
def settings_page():
    return render_template("setting.html")

@app.route("/api/hotel-settings", methods=["GET"])
def get_hotel_settings():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT json_build_object(
            'hotelName', hotelname,
            'shortName', shortname,
            'addressLine1', addressline1,
            'addressLine2', addressline2,
            'city', city,
            'state', state,
            'pincode', pincode,
            'phone', phone,
            'email', email,
            'gstNumber', gstnumber,
            'panNumber', pannumber,
            'printHeader', printheader,
            'printFooter', printfooter,
            'enableLowStockAlert', enablelowstockalert,
            'lowStockThreshold', lowstockthreshold,
            'stockCheckIntervalDays', stockcheckintervaldays
        )
        FROM hotel_master.hotel_settings
        LIMIT 1
    """)

    row = cur.fetchone()

    if not row or not row[0]:
        # No settings in DB → return defaults
        return jsonify({
            "hotelName": "",
            "shortName": "",
            "addressLine1": "",
            "addressLine2": "",
            "city": "",
            "state": "",
            "pincode": "",
            "phone": "",
            "email": "",
            "gstNumber": "",
            "panNumber": "",
            "printHeader": "",
            "printFooter": "",
            "enableLowStockAlert": True,
            "lowStockThreshold": 5,
            "stockCheckIntervalDays": 1
        })

    return jsonify(row[0])




# ---------------------------------------
# SAVE HOTEL SETTINGS (INSERT OR UPDATE)
# ---------------------------------------
@app.route("/api/hotel-settings", methods=["POST"])
def save_hotel_settings():
    data = request.json

    conn = get_db()
    cur = conn.cursor()

    # Check if settings row exists
    cur.execute("SELECT COUNT(*) AS cnt FROM hotel_master.hotel_settings")
    row = cur.fetchone()
    exists = (row is not None and row[0] > 0)

    if exists:
        # UPDATE
        cur.execute("""
            UPDATE hotel_master.hotel_settings SET
                hotelName=%s, shortName=%s, addressLine1=%s, addressLine2=%s,
                city=%s, state=%s, pincode=%s, phone=%s, email=%s,
                gstNumber=%s, panNumber=%s, printHeader=%s, printFooter=%s,
                enableLowStockAlert=%s, lowStockThreshold=%s, stockCheckIntervalDays=%s
        """, (
            data["hotelName"], data["shortName"], data["addressLine1"], data["addressLine2"],
            data["city"], data["state"], data["pincode"], data["phone"], data["email"],
            data["gstNumber"], data["panNumber"], data["printHeader"], data["printFooter"],
            int(data["enableLowStockAlert"]), data["lowStockThreshold"], data["stockCheckIntervalDays"]
        ))
    else:
        # INSERT
        cur.execute("""
            INSERT INTO hotel_master.hotel_settings (
                hotelName, shortName, addressLine1, addressLine2, city, state, pincode, phone, email,
                gstNumber, panNumber, printHeader, printFooter,
                enableLowStockAlert, lowStockThreshold, stockCheckIntervalDays
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data["hotelName"], data["shortName"], data["addressLine1"], data["addressLine2"],
            data["city"], data["state"], data["pincode"], data["phone"], data["email"],
            data["gstNumber"], data["panNumber"], data["printHeader"], data["printFooter"],
            int(data["enableLowStockAlert"]), data["lowStockThreshold"], data["stockCheckIntervalDays"]
        ))

    conn.commit()
    return jsonify({"status": "ok"})

#------- Reportd

@app.route("/reports")
def reports():
    conn = get_db()
    cur = conn.cursor()

    # Load all items for dropdown filter
    cur.execute("SELECT id, item_name FROM hotel_master.item_master ORDER BY item_name")
    items = cur.fetchall()
    
    cur.close()
    conn.close()

    return render_template("reports.html", items=items)


@app.route("/api/reports", methods=["POST"])
def api_reports():
    data = request.json

    start_date = data.get("start_date")
    end_date = data.get("end_date")
    item_id = data.get("item_id")

    conn = get_db()
    cur = conn.cursor()

    query = """
        SELECT 
            oh.order_id,
            oh.table_no,
            oh.created_at,
            SUM(od.qty * od.price) AS amount,
            STRING_AGG(im.item_name || ' × ' || od.qty, ', ') AS items,
            SUM(od.qty) AS total_qty
        FROM hotel_order.order_header oh
        JOIN hotel_order.order_details od ON od.order_id = oh.order_id
        JOIN hotel_master.item_master im ON im.id = od.item_id
        WHERE DATE(oh.created_at) BETWEEN %s AND %s
         and order_status = 'BILLED' 
    """

    params = [start_date, end_date]

    # Apply item filter
    if item_id != "all":
        query += " AND od.item_id = %s"
        params.append(item_id)

    query += """
        GROUP BY oh.order_id, oh.table_no, oh.created_at
        ORDER BY oh.created_at DESC
    """

    cur.execute(query, tuple(params))
    rows = cur.fetchall()

    result = []
    total_orders = 0
    total_revenue = 0
    total_items_sold = 0

    for r in rows:
        total_orders += 1
        total_revenue += float(r[3])
        total_items_sold += int(r[5])

        result.append({
            "order_id": r[0],
            "table_no": r[1],
            "datetime": r[2].strftime("%d-%m-%Y %H:%M:%S"),
            "amount": float(r[3]),
            "items": r[4],
        })

    avg_bill = total_revenue / total_orders if total_orders > 0 else 0

    return jsonify({
        "summary": {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "avg_bill": avg_bill,
            "total_items_sold": total_items_sold
        },
        "rows": result
    })


# ------------------ AUTO OPEN BROWSER ----------------------
def open_browser():
    url = "http://127.0.0.1:5000/login"
    webbrowser.open_new(url)


if __name__ == "__main__":
    threading.Timer(1.5, open_browser).start()
    app.run(debug=True)
