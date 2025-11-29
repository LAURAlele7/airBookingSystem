from flask import Blueprint, render_template, request, session, flash, redirect, url_for, jsonify
from datetime import datetime, timedelta
import uuid
from .utils import login_required, query_all, query_one, execute_sql
from .customer import check_capacity

agent_bp = Blueprint("agent", __name__)

@agent_bp.route("/dashboard")
@login_required(role="agent")
def dashboard():
    """
    Agent Dashboard:
    1. Search & Book Flights (Dynamic Interface)
    2. View Recent Transactions
    """
    email = session.get("user_id")
    
    # 1. Get Allowed Airlines (For display context)
    airlines_data = query_all(
        "SELECT airline_name FROM work_with WHERE agent_email=%s",
        (email,),
    )
    allowed_airlines = [a["airline_name"] for a in airlines_data]


    return render_template(
        "agent_dashboard.html", 
        allowed_airlines=allowed_airlines
    )

@agent_bp.route("/transactions", methods=["GET", "POST"])
@login_required(role="agent")
def transactions():
    """
    View Agent's Transaction History with Filters.
    Merged functionality from previous flights filter.
    """
    email = session.get("user_id")
    
    # Get filter parameters (support both GET and POST)
    start_date = request.values.get('start_date', '').strip()
    end_date = request.values.get('end_date', '').strip()
    origin = request.values.get('origin', '').strip()
    destination = request.values.get('destination', '').strip()
    customer_email = request.values.get('customer_email', '').strip()

    # Base query
    sql = """
        SELECT f.*, t.ticket_ID, p.customer_email, p.purchase_date,
               da.city AS dep_city, aa.city AS arr_city
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        LEFT JOIN airport da ON f.departure_airport = da.name
        LEFT JOIN airport aa ON f.arrival_airport = aa.name
        WHERE p.agent_email=%s
    """
    params = [email]

    # Apply Filters
    if start_date:
        sql += " AND DATE(p.purchase_date) >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(p.purchase_date) <= %s"
        params.append(end_date)
    if origin:
        sql += " AND (f.departure_airport LIKE %s OR da.city LIKE %s)"
        params.extend([f"%{origin}%", f"%{origin}%"])
    if destination:
        sql += " AND (f.arrival_airport LIKE %s OR aa.city LIKE %s)"
        params.extend([f"%{destination}%", f"%{destination}%"])
    if customer_email:
        sql += " AND p.customer_email LIKE %s"
        params.append(f"%{customer_email}%")

    sql += " ORDER BY p.purchase_date DESC LIMIT 50"
    
    recent_purchases = query_all(sql, tuple(params))
    
    return render_template(
        "agent_transactions.html", 
        recent_purchases=recent_purchases,
        # Pass back values to repopulate form
        filters={
            'start_date': start_date,
            'end_date': end_date,
            'origin': origin,
            'destination': destination,
            'customer_email': customer_email
        }
    )

@agent_bp.route("/api/agent_airports")
@login_required(role="agent")
def get_agent_airports():
    """
    Return distinct origins and destinations ONLY for airlines the agent works with.
    """
    email = session.get("user_id")
    
    # 1. Get Allowed Airlines
    airlines_data = query_all(
        "SELECT airline_name FROM work_with WHERE agent_email=%s",
        (email,),
    )
    allowed_airlines = [a["airline_name"] for a in airlines_data]
    
    if not allowed_airlines:
        return jsonify({"origins": [], "destinations": []})

    # Prepare SQL for IN clause
    placeholders = ",".join(["%s"] * len(allowed_airlines))
    
    # Get distinct departure airports for these airlines
    sql_origins = f"""
        SELECT DISTINCT f.departure_airport AS code, a.city
        FROM flight f
        JOIN airport a ON f.departure_airport = a.name
        WHERE f.airline_name IN ({placeholders})
          AND f.status IN ('upcoming', 'Delayed') 
          AND f.departure_time > NOW()
        ORDER BY a.city
    """
    origins = query_all(sql_origins, tuple(allowed_airlines))

    # Get distinct arrival airports for these airlines
    sql_dests = f"""
        SELECT DISTINCT f.arrival_airport AS code, a.city
        FROM flight f
        JOIN airport a ON f.arrival_airport = a.name
        WHERE f.airline_name IN ({placeholders})
          AND f.status IN ('upcoming', 'Delayed') 
          AND f.departure_time > NOW()
        ORDER BY a.city
    """
    dests = query_all(sql_dests, tuple(allowed_airlines))

    return jsonify({
        "origins": origins,
        "destinations": dests
    })

@agent_bp.route("/api/agent_customers")
@login_required(role="agent")
def api_agent_customers():
    """Return list of customers this agent has dealt with for autocomplete."""
    email = session.get("user_id")
    # Fetch distinct customers from purchases table for this agent
    sql = "SELECT DISTINCT customer_email FROM purchases WHERE agent_email=%s ORDER BY customer_email"
    customers = query_all(sql, (email,))
    # Extract just the emails list
    email_list = [c['customer_email'] for c in customers]
    return jsonify(email_list)

@agent_bp.route("/api/agent_transactions")
@login_required(role="agent")
def api_agent_transactions():
    """
    API to fetch agent transaction history dynamically.
    """
    email = session.get("user_id")
    
    # Get filter parameters
    start_date = request.args.get('start_date', '').strip()
    end_date = request.args.get('end_date', '').strip()
    origin = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    customer_email = request.args.get('customer_email', '').strip()

    # Base query
    sql = """
        SELECT f.*, t.ticket_ID, p.customer_email, p.purchase_date,
               da.city AS dep_city, aa.city AS arr_city
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        LEFT JOIN airport da ON f.departure_airport = da.name
        LEFT JOIN airport aa ON f.arrival_airport = aa.name
        WHERE p.agent_email=%s
    """
    params = [email]

    # Apply Filters
    if start_date:
        sql += " AND DATE(p.purchase_date) >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND DATE(p.purchase_date) <= %s"
        params.append(end_date)
    if origin:
        sql += " AND (f.departure_airport LIKE %s OR da.city LIKE %s)"
        params.extend([f"%{origin}%", f"%{origin}%"])
    if destination:
        sql += " AND (f.arrival_airport LIKE %s OR aa.city LIKE %s)"
        params.extend([f"%{destination}%", f"%{destination}%"])
    if customer_email:
        sql += " AND p.customer_email LIKE %s"
        params.append(f"%{customer_email}%")

    sql += " ORDER BY p.purchase_date DESC LIMIT 50"
    
    transactions = query_all(sql, tuple(params))
    
    # Serialize for JSON
    for t in transactions:
        if t.get('purchase_date'): t['purchase_date'] = str(t['purchase_date'])
        if t.get('departure_time'): t['departure_time'] = str(t['departure_time'])
        if t.get('arrival_time'): t['arrival_time'] = str(t['arrival_time'])
        if 'price' in t: t['price'] = str(t['price'])
        
    return jsonify(transactions)

@agent_bp.route("/api/agent_airports")


@agent_bp.route("/api/agent_transaction_airports")
@login_required(role="agent")
def get_agent_transaction_airports():
    """
    Return distinct origins and destinations found in the agent's transaction history.
    Used for filtering the transaction list.
    """
    email = session.get("user_id")
    
    # Origins from history
    sql_origins = """
        SELECT DISTINCT f.departure_airport AS code, da.city
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        JOIN airport da ON f.departure_airport = da.name
        WHERE p.agent_email = %s
        ORDER BY da.city
    """
    origins = query_all(sql_origins, (email,))

    # Destinations from history
    sql_dests = """
        SELECT DISTINCT f.arrival_airport AS code, aa.city
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        JOIN airport aa ON f.arrival_airport = aa.name
        WHERE p.agent_email = %s
        ORDER BY aa.city
    """
    dests = query_all(sql_dests, (email,))

    return jsonify({
        "origins": origins,
        "destinations": dests
    })

@agent_bp.route("/api/search_flights")
@login_required(role="agent")
def search_flights_api():
    """
    API for Agent Dynamic Search.
    Strictly limits results to airlines the agent works with.
    """
    email = session.get("user_id")
    
    # 1. Get Allowed Airlines
    airlines_data = query_all(
        "SELECT airline_name FROM work_with WHERE agent_email=%s",
        (email,),
    )
    allowed_airlines = [a["airline_name"] for a in airlines_data]
    
    # If agent has no airlines, return empty list immediately
    if not allowed_airlines:
        return jsonify([])

    origin = request.args.get("origin", "").strip()
    destination = request.args.get("destination", "").strip()
    date = request.args.get("date", "").strip()

    # Build Query
    conditions = [
        "f.status IN ('upcoming', 'Delayed')",
        "f.remaining_seats > 0",
        "f.departure_time > NOW()"
    ]
    
    # CRITICAL: Restrict to allowed airlines
    conditions.append("f.airline_name IN ({})".format(
        ",".join(["%s"] * len(allowed_airlines))
    ))
    params = list(allowed_airlines)

    if origin:
        conditions.append("(f.departure_airport LIKE %s OR da.city LIKE %s)")
        params.extend([f"%{origin}%", f"%{origin}%"])
    if destination:
        conditions.append("(f.arrival_airport LIKE %s OR aa.city LIKE %s)")
        params.extend([f"%{destination}%", f"%{destination}%"])
    if date:
        conditions.append("DATE(f.departure_time) = %s")
        params.append(date)

    where_clause = " AND ".join(conditions)
    
    # Join with airport for city names
    sql = f"""
        SELECT f.*, da.city AS dep_city, aa.city AS arr_city
        FROM flight f
        JOIN airport da ON f.departure_airport = da.name
        JOIN airport aa ON f.arrival_airport = aa.name
        WHERE {where_clause}
        ORDER BY f.departure_time ASC
        LIMIT 50
    """
    
    try:
        flights = query_all(sql, tuple(params))
        # Serialization
        for f in flights:
            if f.get('departure_time'): f['departure_time'] = str(f['departure_time'])
            if f.get('arrival_time'): f['arrival_time'] = str(f['arrival_time'])
            if 'price' in f: f['price'] = str(f['price'])
        return jsonify(flights)
    except Exception as e:
        print(f"Error in agent search api: {e}")
        return jsonify([])


@agent_bp.route("/book_ticket", methods=["GET"])
@login_required(role="agent")
def book_ticket():
    """
    Render the booking confirmation page for an agent.
    """
    airline = request.args.get("airline")
    flight_num = request.args.get("flight_number")
    
    if not airline or not flight_num:
        flash("Invalid flight selection.", "warning")
        return redirect(url_for("agent.dashboard"))

    # Fetch flight details with city names
    sql = """
        SELECT f.*, da.city AS dep_city, aa.city AS arr_city
        FROM flight f
        LEFT JOIN airport da ON f.departure_airport = da.name
        LEFT JOIN airport aa ON f.arrival_airport = aa.name
        WHERE f.airline_name=%s AND f.flight_number=%s
    """
    flight = query_one(sql, (airline, flight_num))
    
    if not flight:
        flash("Flight not found.", "danger")
        return redirect(url_for("agent.dashboard"))
        
    return render_template("agent_booking.html", flight=flight)

@agent_bp.route("/flights", methods=["GET", "POST"])
@login_required(role="agent")
def flights():
    email = session.get("user_id")
    flights = []
    if request.method == "POST":
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        origin = request.form.get("origin", "").strip()
        destination = request.form.get("destination", "").strip()

        conditions = ["p.agent_email=%s"]
        params = [email]

        if start_date:
            conditions.append("DATE(p.purchase_date) >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(p.purchase_date) <= %s")
            params.append(end_date)

        if origin:
            conditions.append("f.departure_airport=%s")
            params.append(origin)
        if destination:
            conditions.append("f.arrival_airport=%s")
            params.append(destination)

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT f.*, t.ticket_ID, p.customer_email, p.purchase_date
            FROM purchases p
            JOIN ticket t ON p.ticket_ID = t.ticket_ID
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
            WHERE {where_clause}
            ORDER BY p.purchase_date DESC
        """
        flights = query_all(sql, tuple(params))

    return render_template("agent_flights.html", flights=flights)


@agent_bp.route("/purchase", methods=["POST"])
@login_required(role="agent")
def purchase():
    """
    agent 代表 customer 购票
    - 购买成功时，减少 flight.remaining_seats 计数。
    """
    agent_email = session.get("user_id")
    customer_email = request.form.get("customer_email", "").strip()
    airline_name = request.form.get("airline_name")
    flight_number = request.form.get("flight_number")

    # 1. 基础数据校验
    if not customer_email or not airline_name or not flight_number:
        flash("Missing flight or customer data.", "danger")
        return redirect(url_for("agent.dashboard"))

    # 2. 确认 customer 存在
    cust = query_one("SELECT email FROM customer WHERE email=%s", (customer_email,))
    if not cust:
        flash(f"Customer '{customer_email}' not found. Please ensure the email is correct.", "danger")
        return redirect(url_for("agent.dashboard"))

    # 3. 确认 agent 和 airline work_with
    rel = query_one(
        "SELECT * FROM work_with WHERE agent_email=%s AND airline_name=%s",
        (agent_email, airline_name),
    )
    if not rel:
        flash("You are not allowed to sell tickets for this airline.", "danger")
        return redirect(url_for("agent.dashboard"))

    # 4. 检查舱位 (使用 check_capacity)
    ok, msg = check_capacity(airline_name, flight_number)
    if not ok:
        flash(msg, "warning")
        return redirect(url_for("agent.dashboard"))

    # 5. 获取航班价格
    flight = query_one(
        "SELECT price FROM flight WHERE airline_name=%s AND flight_number=%s",
        (airline_name, flight_number),
    )
    if not flight:
        flash("Flight not found.", "danger")
        return redirect(url_for("agent.dashboard"))

    price = flight["price"]
    # 使用 UUID 生成 Ticket ID
    ticket_id = str(uuid.uuid4())[:8].upper() 
    purchase_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 6. 执行购买事务
    try:
        # a. 插入到 ticket 表
        execute_sql(
            """
            INSERT INTO ticket (ticket_ID, ticket_price, ticket_status, airline_name, flight_number)
            VALUES (%s, %s, 'Confirmed', %s, %s)
            """,
            (ticket_id, price, airline_name, flight_number),
        )
        
        # b. 插入到 purchases 表 (Agent 销售记录)
        execute_sql(
            """
            INSERT INTO purchases (customer_email, agent_email, ticket_ID, purchase_date)
            VALUES (%s, %s, %s, %s)
            """,
            (customer_email, agent_email, ticket_id, purchase_date),
        )
        
        # c. 关键步骤：减少剩余座位
        execute_sql(
            """
            UPDATE flight SET remaining_seats = remaining_seats - 1
            WHERE airline_name=%s AND flight_number=%s
            """,
            (airline_name, flight_number),
        )
        
        flash(f"Success! Ticket {ticket_id} purchased for {customer_email} on Flight {flight_number}.", "success")
        
    except Exception as e:
        flash(f"Purchase failed: Transaction Error. Please check logs. Details: {e}", "danger")
    
    return redirect(url_for("agent.dashboard"))

@agent_bp.route("/analytics")
@login_required(role="agent")
def analytics():
    """
    Agent Analytics:
    1. Commission stats (Total, Average, Count)
    2. Top 5 Customers by Tickets (Last 6 Months)
    3. Top 5 Customers by Commission (Last Year)
    """
    email = session.get("user_id")
    
    # 1. General Commission Stats (Existing logic assumed, or added here)
    # Calculate total commission (10% of price)
    sql_stats = """
        SELECT 
            COUNT(*) as total_tickets,
            SUM(f.price * 0.10) as total_commission,
            AVG(f.price * 0.10) as avg_commission
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE p.agent_email=%s AND p.purchase_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
    """
    stats = query_one(sql_stats, (email,))
    
    # 2. Top 5 Customers by Tickets (Last 6 Months)
    sql_top_tickets = """
        SELECT p.customer_email, COUNT(*) as ticket_count
        FROM purchases p
        WHERE p.agent_email=%s 
          AND p.purchase_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
        GROUP BY p.customer_email
        ORDER BY ticket_count DESC
        LIMIT 5
    """
    top_tickets = query_all(sql_top_tickets, (email,))
    
    # 3. Top 5 Customers by Commission (Last Year)
    sql_top_commission = """
        SELECT p.customer_email, SUM(f.price * 0.10) as total_comm
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE p.agent_email=%s 
          AND p.purchase_date >= DATE_SUB(NOW(), INTERVAL 1 YEAR)
        GROUP BY p.customer_email
        ORDER BY total_comm DESC
        LIMIT 5
    """
    top_commission = query_all(sql_top_commission, (email,))

    return render_template(
        "agent_analytics.html", 
        stats=stats,
        top_tickets=top_tickets,
        top_commission=top_commission
    )