from flask import Blueprint, render_template, request, session, flash, redirect, url_for, jsonify
from datetime import datetime, timedelta

from .utils import (
    login_required,
    staff_permission_required,
    query_all,
    query_one,
    execute_sql,
)

staff_bp = Blueprint("staff", __name__)

@staff_bp.before_request
def check_staff_access():
    """Ensure only logged-in staff can access these routes."""
    if session.get("role") not in ["staff", "admin", "operator"]:
        # Adjust roles based on your actual session keys
        # For this example, assuming 'staff' covers all or specific checks are done inside
        pass

@staff_bp.route("/dashboard")
@login_required(role="staff")
def dashboard():
    airline_name = session.get("airline_name")
    
    # Base query for the next 30 days
    sql = """
        SELECT * FROM flight 
        WHERE airline_name = %s 
        AND departure_time BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 30 DAY)
    """
    params = [airline_name]

    # Apply Filters
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    origin = request.args.get("origin")
    dest = request.args.get("destination")

    if start_date:
        sql += " AND departure_time >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND departure_time <= %s"
        params.append(end_date)
    if origin:
        sql += " AND (departure_airport LIKE %s OR departure_airport IN (SELECT name FROM airport WHERE city LIKE %s))"
        params.extend([f"%{origin}%", f"%{origin}%"])
    if dest:
        sql += " AND (arrival_airport LIKE %s OR arrival_airport IN (SELECT name FROM airport WHERE city LIKE %s))"
        params.extend([f"%{dest}%", f"%{dest}%"])

    sql += " ORDER BY departure_time ASC"
    
    flights = query_all(sql, tuple(params))
    return render_template("staff_dashboard.html", flights=flights, airline_name=airline_name)

@staff_bp.route("/passengers", methods=["GET", "POST"])
@login_required(role="staff")
def passengers():
    airline_name = session.get("airline_name")
    selected_flight_num = request.args.get("flight_number") or request.form.get("flight_number")
    passengers_list = []

    if selected_flight_num:
        # Fetch passengers for this flight
        # JOIN ticket -> purchases -> customer
        sql = """
            SELECT c.name, c.email, t.ticket_ID 
            FROM ticket t
            JOIN purchases p ON t.ticket_ID = p.ticket_ID
            JOIN customer c ON p.customer_email = c.email
            WHERE t.airline_name = %s AND t.flight_number = %s
        """
        passengers_list = query_all(sql, (airline_name, selected_flight_num))

    # Always fetch the list of flights so the user can switch/select
    flights_sql = "SELECT * FROM flight WHERE airline_name = %s ORDER BY departure_time DESC LIMIT 50"
    flights = query_all(flights_sql, (airline_name,))


    return render_template("staff_passengers.html", 
                           flights=flights, 
                           passengers=passengers_list, 
                           selected_flight=selected_flight_num)

@staff_bp.route("/customer-history", methods=["GET", "POST"])
@login_required(role="staff")
def customer_history():
    airline_name = session.get("airline_name")
    customer_email = request.args.get("customer_email") or request.form.get("customer_email")
    customer_flights = []

    if customer_email:
        sql = """
            SELECT f.*, t.ticket_ID 
            FROM ticket t
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
            WHERE t.airline_name = %s AND t.customer_email = %s
            ORDER BY f.departure_time DESC
        """
        customer_flights = query_all(sql, (airline_name, customer_email))

    recent_customers_sql = """
        SELECT DISTINCT customer_email FROM ticket 
        WHERE airline_name = %s 
        ORDER BY ticket_ID DESC LIMIT 20
    """
    recent_customers = [r['customer_email'] for r in query_all(recent_customers_sql, (airline_name,))]

    return render_template(
        "staff_customer_flights.html", 
        flights=customer_flights, 
        recent_customers=recent_customers,
        selected_email=customer_email
    )



@staff_bp.route("/customer_flights", methods=["GET", "POST"])
@login_required(role="staff")
def customer_flights():
    """
    查看某 customer 在本 airline 的所有航班
    """
    username = session.get("user_id")
    staff = query_one("SELECT * FROM staff WHERE username=%s", (username,))
    airline_name = staff["airline_name"] if staff else None

    flights = []
    if request.method == "POST":
        customer_email = request.form.get("customer_email", "").strip()
        if not customer_email:
            flash("Customer email required.")
        else:
            sql = """
                SELECT f.*, t.ticket_ID, p.purchase_date
                FROM purchases p
                JOIN ticket t ON p.ticket_ID = t.ticket_ID
                JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
                WHERE p.customer_email=%s AND f.airline_name=%s
                ORDER BY f.departure_time DESC
            """
            flights = query_all(sql, (customer_email, airline_name))

    return render_template("staff_customer_flights.html", flights=flights, airline_name=airline_name)


@staff_bp.route("/analytics")
@login_required(role="staff")
def analytics():
    """
    Analytics:
    - Top booking agents by month / year (by tickets & commission)
    - Most frequent customer (last year)
    - Tickets sold per month
    - Delay vs on-time
    - Top destinations (last 3 months & last year)
    """
    username = session.get("user_id")
    staff = query_one("SELECT * FROM staff WHERE username=%s", (username,))
    airline_name = staff["airline_name"]

    # top agents by tickets / commission in last month/year
    sql_top_agent_month = """
        SELECT p.agent_email,
               COUNT(*) AS ticket_count,
               COALESCE(SUM(t.ticket_price*0.1), 0) AS commission
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
          AND p.agent_email IS NOT NULL
        GROUP BY p.agent_email
        ORDER BY ticket_count DESC
        LIMIT 5
    """
    top_agent_month = query_all(sql_top_agent_month, (airline_name,))

    sql_top_agent_year = """
        SELECT p.agent_email,
               COUNT(*) AS ticket_count,
               COALESCE(SUM(t.ticket_price*0.1), 0) AS commission
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
          AND p.agent_email IS NOT NULL
        GROUP BY p.agent_email
        ORDER BY ticket_count DESC
        LIMIT 5
    """
    top_agent_year = query_all(sql_top_agent_year, (airline_name,))

    # most frequent customer last year
    sql_freq_cust = """
        SELECT p.customer_email, COUNT(*) AS cnt
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
        GROUP BY p.customer_email
        ORDER BY cnt DESC
        LIMIT 1
    """
    most_freq_customer = query_one(sql_freq_cust, (airline_name,))

    # tickets sold per month
    sql_tickets_month = """
        SELECT DATE_FORMAT(p.purchase_date, '%%Y-%%m') AS month,
               COUNT(*) AS cnt
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
        GROUP BY month
        ORDER BY month
    """
    tickets_month = query_all(sql_tickets_month, (airline_name,))
    months = [r["month"] for r in tickets_month]
    counts = [int(r["cnt"]) for r in tickets_month]

    # delay vs on-time stats
    sql_delay = """
        SELECT status, COUNT(*) AS cnt
        FROM flight
        WHERE airline_name=%s
        GROUP BY status
    """
    delay_stats = query_all(sql_delay, (airline_name,))
    statuses = [r["status"] for r in delay_stats]
    status_counts = [int(r["cnt"]) for r in delay_stats]

    # top destinations last 3 months / last year
    sql_top_dest_3m = """
        SELECT f.arrival_airport, COUNT(*) AS cnt
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 3 MONTH)
        GROUP BY f.arrival_airport
        ORDER BY cnt DESC
        LIMIT 5
    """
    top_dest_3m = query_all(sql_top_dest_3m, (airline_name,))

    sql_top_dest_1y = """
        SELECT f.arrival_airport, COUNT(*) AS cnt
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
        GROUP BY f.arrival_airport
        ORDER BY cnt DESC
        LIMIT 5
    """
    top_dest_1y = query_all(sql_top_dest_1y, (airline_name,))

    return render_template(
        "staff_analytics.html",
        airline_name=airline_name,
        top_agent_month=top_agent_month,
        top_agent_year=top_agent_year,
        most_freq_customer=most_freq_customer,
        months=months,
        counts=counts,
        statuses=statuses,
        status_counts=status_counts,
        top_dest_3m=top_dest_3m,
        top_dest_1y=top_dest_1y,
    )


# ---------- Admin 功能 ----------

@staff_bp.route("/admin/airport", methods=["GET", "POST"])
@login_required(role="staff")
@staff_permission_required("Admin")
def add_airport():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        city = request.form.get("city", "").strip()
        if not name or not city:
            flash("Name and city are required.")
        else:
            try:
                execute_sql(
                    "INSERT INTO airport (name, city) VALUES (%s, %s)",
                    (name, city),
                )
                flash("Airport added.")
            except Exception as e:
                flash(f"Error: {e}")
    return render_template("staff_admin_airport.html")


@staff_bp.route("/admin/airplane", methods=["GET", "POST"])
@login_required(role="staff")
@staff_permission_required("Admin")
def add_airplane():
    username = session.get("user_id")
    staff = query_one("SELECT * FROM staff WHERE username=%s", (username,))
    airline_name = staff["airline_name"] if staff else None

    if request.method == "POST":
        airplane_id = request.form.get("airplane_id", "").strip()
        seat_capacity = request.form.get("seat_capacity", "").strip()
        if not airplane_id or not seat_capacity:
            flash("Airplane ID and seat capacity are required.")
        else:
            try:
                execute_sql(
                    "INSERT INTO airplane (airplane_id, airline_name, seat_capacity) VALUES (%s, %s, %s)",
                    (airplane_id, airline_name, seat_capacity),
                )
                flash("Airplane added.")
            except Exception as e:
                flash(f"Error: {e}")
    return render_template("staff_admin_airplane.html", airline_name=airline_name)


@staff_bp.route("/admin/flight", methods=["GET", "POST"])
@login_required(role="staff")
@staff_permission_required("Admin")
def add_flight():
    username = session.get("user_id")
    staff = query_one("SELECT * FROM staff WHERE username=%s", (username,))
    airline_name = staff["airline_name"] if staff else None

    if request.method == "POST":
        flight_number = request.form.get("flight_number", "").strip()
        departure_airport = request.form.get("departure_airport", "").strip()
        arrival_airport = request.form.get("arrival_airport", "").strip()
        departure_time = request.form.get("departure_time", "").strip()
        arrival_time = request.form.get("arrival_time", "").strip()
        price = request.form.get("price", "").strip()
        status = request.form.get("status", "upcoming")
        airplane_assigned = request.form.get("airplane_assigned", "").strip()

        if not (flight_number and departure_airport and arrival_airport and
                departure_time and arrival_time and price and airplane_assigned):
            flash("All fields are required.")
        else:
            try:
                execute_sql(
                    """
                    INSERT INTO flight
                    (flight_number, airline_name, departure_airport, arrival_airport,
                     departure_time, arrival_time, price, status, airplane_assigned)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        flight_number, airline_name, departure_airport, arrival_airport,
                        departure_time, arrival_time, price, status, airplane_assigned,
                    ),
                )
                flash("Flight created.")
            except Exception as e:
                flash(f"Error: {e}")

    return render_template("staff_admin_flight.html", airline_name=airline_name)


@staff_bp.route("/admin/agent", methods=["GET", "POST"])
@login_required(role="staff")
@staff_permission_required("Admin")
def add_agent():
    """
    关联 booking agent 和 airline
    """
    username = session.get("user_id")
    staff = query_one("SELECT * FROM staff WHERE username=%s", (username,))
    airline_name = staff["airline_name"] if staff else None

    if request.method == "POST":
        agent_email = request.form.get("agent_email", "").strip()
        if not agent_email:
            flash("Agent email is required.")
        else:
            # 确认 agent 存在
            agent = query_one("SELECT * FROM booking_agent WHERE email=%s", (agent_email,))
            if not agent:
                flash("Booking agent not found.")
            else:
                try:
                    execute_sql(
                        "INSERT INTO work_with (agent_email, airline_name) VALUES (%s, %s)",
                        (agent_email, airline_name),
                    )
                    flash("Agent associated with airline.")
                except Exception as e:
                    flash(f"Error: {e}")
    return render_template("staff_admin_agent.html", airline_name=airline_name)


# ---------- Operator 功能 ----------

@staff_bp.route("/operator/status", methods=["GET", "POST"])
@login_required(role="staff")
def update_status():
    airline_name = session.get("airline_name")

    if request.method == "POST":
        flight_num = request.form.get("flight_number")
        new_status = request.form.get("status")
        
        # Update query
        sql = "UPDATE flight SET status=%s WHERE airline_name=%s AND flight_number=%s"
        query_one(sql, (new_status, airline_name, flight_num)) # query_one/all can be used for updates too usually
        flash(f"Flight {flight_num} status updated to {new_status}.")
        return redirect(url_for("staff.update_status"))

    # GET: Show all upcoming/in-progress flights to allow selection
    sql = """
        SELECT * FROM flight 
        WHERE airline_name = %s 
        AND status NOT IN ('cancelled', 'arrived')
        ORDER BY departure_time ASC
    """
    flights = query_all(sql, (airline_name,))
    return render_template("staff_operator_status.html", flights=flights)


@staff_bp.route("/api/get_customers")
@login_required(role="staff")
def get_customers():
    """Fetch customer emails for suggestions."""
    airline_name = session.get("airline_name")
    try:
        # Get customers who have purchased tickets from this airline
        sql = """
            SELECT DISTINCT p.customer_email 
            FROM purchases p
            JOIN ticket t ON p.ticket_ID = t.ticket_ID
            WHERE t.airline_name = %s
        """
        customers = query_all(sql, (airline_name,))
        return jsonify([c['customer_email'] for c in customers])
    except Exception as e:
        return jsonify([])