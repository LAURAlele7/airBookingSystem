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


def _get_staff_and_airline():
    """Helper: return (staff_row_or_None, airline_name_or_None)."""
    username = session.get("user_id")
    if not username:
        return None, session.get("airline_name")
    staff = query_one("SELECT * FROM staff WHERE username=%s", (username,))
    airline_name = staff["airline_name"] if staff and staff.get("airline_name") else session.get("airline_name")
    return staff, airline_name


@staff_bp.before_request
def check_staff_access():
    """Ensure only logged-in staff can access these routes."""
    if session.get("role") not in ["staff", "admin", "operator"]:
        # You may want to redirect or abort here in real app.
        pass


@staff_bp.route("/dashboard")
@login_required(role="staff")
def dashboard():
    staff, airline_name = _get_staff_and_airline()

    permissions = []
    if staff:
        # Query the permission table (assuming standard schema: username, permission_type)
        p_rows = query_all("SELECT permission_type FROM permission WHERE username=%s", (staff['username'],))
        permissions = [r['permission_type'] for r in p_rows]

    # Updated SQL to include city names
    sql = """
        SELECT f.*, da.city AS dep_city, aa.city AS arr_city
        FROM flight f
        LEFT JOIN airport da ON f.departure_airport = da.name
        LEFT JOIN airport aa ON f.arrival_airport = aa.name
        WHERE f.airline_name = %s
          AND f.departure_time BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 30 DAY)
    """
    params = [airline_name]

    # Apply Filters
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    origin = request.args.get("origin")
    dest = request.args.get("destination")

    if start_date:
        sql += " AND f.departure_time >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND f.departure_time <= %s"
        params.append(end_date)
    if origin:
        sql += " AND (f.departure_airport LIKE %s OR da.city LIKE %s)"
        params.extend([f"%{origin}%", f"%{origin}%"])
    if dest:
        sql += " AND (f.arrival_airport LIKE %s OR aa.city LIKE %s)"
        params.extend([f"%{dest}%", f"%{dest}%"])

    sql += " ORDER BY f.departure_time ASC"

    flights = query_all(sql, tuple(params))
    return render_template("staff_dashboard.html", flights=flights, airline_name=airline_name, permissions=permissions)

@staff_bp.route("/passengers", methods=["GET", "POST"])
@login_required(role="staff")
def passengers():
    _, airline_name = _get_staff_and_airline()
    selected_flight_num = request.args.get("flight_number") or request.form.get("flight_number")
    passengers_list = []

    if selected_flight_num:
        # Fetch passengers for this flight by joining through purchases
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

    return render_template(
        "staff_passengers.html",
        flights=flights,
        passengers=passengers_list,
        selected_flight=selected_flight_num,
        airline_name=airline_name,
    )

@staff_bp.route("/customer_flights")
@login_required(role="staff")
def customer_flights():
    """Render the Customer Flight History page."""
    _, airline_name = _get_staff_and_airline()
    return render_template("staff_customer_flights.html", airline_name=airline_name)


@staff_bp.route("/api/customer_flights")
@login_required(role="staff")
def api_customer_flights():
    """API to fetch flight history. If customer_email provided, filter by it. Else show recent."""
    _, airline_name = _get_staff_and_airline()
    customer_email = request.args.get("customer_email", "").strip()
    
    # Modified SQL to handle optional customer_email and include it in result
    sql = """
        SELECT t.ticket_ID, f.flight_number, f.departure_airport, f.arrival_airport, 
               f.departure_time, f.arrival_time, f.status,
               da.city AS dep_city, aa.city AS arr_city,
               p.customer_email
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        LEFT JOIN airport da ON f.departure_airport = da.name
        LEFT JOIN airport aa ON f.arrival_airport = aa.name
        WHERE f.airline_name = %s
    """
    params = [airline_name]

    if customer_email:
        sql += " AND p.customer_email = %s"
        params.append(customer_email)

    sql += " ORDER BY f.departure_time DESC LIMIT 50"

    flights = query_all(sql, tuple(params))
    
    # Serialize dates
    for f in flights:
        if f.get('departure_time'): f['departure_time'] = str(f['departure_time'])
        if f.get('arrival_time'): f['arrival_time'] = str(f['arrival_time'])
        
    return jsonify(flights)


@staff_bp.route("/analytics")
@login_required(role="staff")
def analytics():
    staff, airline_name = _get_staff_and_airline()

    # Top agents (month) - by ticket count
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

    # Top agents (year) - by ticket count
    sql_top_agent_year = sql_top_agent_month.replace("1 MONTH", "1 YEAR")
    top_agent_year = query_all(sql_top_agent_year, (airline_name,))

    # Top agents (year) - by commission
    sql_top_agent_commission_year = """
        SELECT p.agent_email,
               COALESCE(SUM(t.ticket_price*0.1), 0) AS total_commission
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE f.airline_name=%s
          AND p.purchase_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
          AND p.agent_email IS NOT NULL
        GROUP BY p.agent_email
        ORDER BY total_commission DESC
        LIMIT 5
    """
    top_agent_commission_year = query_all(sql_top_agent_commission_year, (airline_name,))

    # Top agents (month) - by commission
    sql_top_agent_commission_month = sql_top_agent_commission_year.replace("1 YEAR", "1 MONTH")
    top_agent_commission_month = query_all(sql_top_agent_commission_month, (airline_name,))

    # Most frequent customer last year
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

    sql_top_dest_1y = sql_top_dest_3m.replace("3 MONTH", "1 YEAR")
    top_dest_1y = query_all(sql_top_dest_1y, (airline_name,))

    return render_template(
        "staff_analytics.html",
        airline_name=airline_name,
        top_agent_month=top_agent_month,
        top_agent_year=top_agent_year,
        top_agent_commission_year=top_agent_commission_year,
        top_agent_commission_month=top_agent_commission_month,
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
                execute_sql("INSERT INTO airport (name, city) VALUES (%s, %s)", (name, city))
                flash("Airport added.")
            except Exception as e:
                flash(f"Error: {e}")
    
    # Fetch all airports to display
    airports = query_all("SELECT * FROM airport ORDER BY city, name")
    return render_template("staff_admin_airport.html", airports=airports)


@staff_bp.route("/admin/airplane", methods=["GET", "POST"])
@login_required(role="staff")
@staff_permission_required("Admin")
def add_airplane():
    staff, airline_name = _get_staff_and_airline()

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
    
    # Fetch existing airplanes for this airline
    airplanes = query_all("SELECT * FROM airplane WHERE airline_name=%s ORDER BY airplane_id", (airline_name,))
    return render_template("staff_admin_airplane.html", airline_name=airline_name, airplanes=airplanes)


@staff_bp.route("/admin/flight", methods=["GET", "POST"])
@login_required(role="staff")
@staff_permission_required("Admin")
def add_flight():
    staff, airline_name = _get_staff_and_airline()

    if request.method == "POST":
        flight_number = request.form.get("flight_number", "").strip()
        departure_airport = request.form.get("departure_airport", "").strip()
        arrival_airport = request.form.get("arrival_airport", "").strip()
        departure_time = request.form.get("departure_time", "").strip()
        arrival_time = request.form.get("arrival_time", "").strip()
        price = request.form.get("price", "").strip()
        status = request.form.get("status", "upcoming")
        airplane_assigned = request.form.get("airplane_assigned", "").strip()

        if not (flight_number and departure_airport and arrival_airport and departure_time and arrival_time and price and airplane_assigned):
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

    # Fetch recent flights for display
    flights = query_all("SELECT * FROM flight WHERE airline_name=%s ORDER BY departure_time DESC LIMIT 20", (airline_name,))
    return render_template("staff_admin_flight.html", airline_name=airline_name, flights=flights)


@staff_bp.route("/admin/agent", methods=["GET", "POST"])
@login_required(role="staff")
@staff_permission_required("Admin")
def add_agent():
    staff, airline_name = _get_staff_and_airline()

    if request.method == "POST":
        agent_email = request.form.get("agent_email", "").strip()
        if not agent_email:
            flash("Agent email is required.")
        else:
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
    
    # Fetch existing agents
    agents = query_all("SELECT agent_email FROM work_with WHERE airline_name=%s", (airline_name,))
    return render_template("staff_admin_agent.html", airline_name=airline_name, agents=agents)


# --- Deletion Routes ---

# @staff_bp.route("/admin/flight/delete", methods=["POST"])
# @login_required(role="staff")
# @staff_permission_required("Admin")
# def delete_flight():
#     _, airline_name = _get_staff_and_airline()
#     flight_number = request.form.get("flight_number")
#     if flight_number:
#         try:
#             execute_sql("DELETE FROM flight WHERE airline_name=%s AND flight_number=%s", (airline_name, flight_number))
#             flash(f"Flight {flight_number} deleted.")
#         except Exception as e:
#             flash(f"Error deleting flight (it may have associated tickets): {e}")
#     return redirect(url_for("staff.add_flight"))

# @staff_bp.route("/admin/airplane/delete", methods=["POST"])
# @login_required(role="staff")
# @staff_permission_required("Admin")
# def delete_airplane():
#     _, airline_name = _get_staff_and_airline()
#     airplane_id = request.form.get("airplane_id")
#     if airplane_id:
#         try:
#             execute_sql("DELETE FROM airplane WHERE airline_name=%s AND airplane_id=%s", (airline_name, airplane_id))
#             flash(f"Airplane {airplane_id} deleted.")
#         except Exception as e:
#             flash(f"Error deleting airplane (it may be assigned to flights): {e}")
#     return redirect(url_for("staff.add_airplane"))

# @staff_bp.route("/admin/airport/delete", methods=["POST"])
# @login_required(role="staff")
# @staff_permission_required("Admin")
# def delete_airport():
#     name = request.form.get("name")
#     if name:
#         try:
#             execute_sql("DELETE FROM airport WHERE name=%s", (name,))
#             flash(f"Airport {name} deleted.")
#         except Exception as e:
#             flash(f"Error deleting airport (it may be used in flights): {e}")
#     return redirect(url_for("staff.add_airport"))

# @staff_bp.route("/admin/agent/delete", methods=["POST"])
# @login_required(role="staff")
# @staff_permission_required("Admin")
# def delete_agent():
#     _, airline_name = _get_staff_and_airline()
#     agent_email = request.form.get("agent_email")
#     if agent_email:
#         try:
#             execute_sql("DELETE FROM work_with WHERE airline_name=%s AND agent_email=%s", (airline_name, agent_email))
#             flash(f"Agent {agent_email} removed from airline.")
#         except Exception as e:
#             flash(f"Error removing agent: {e}")
#     return redirect(url_for("staff.add_agent"))


# ---------- Operator 功能 ----------

@staff_bp.route("/operator/status", methods=["GET", "POST"])
@login_required(role="staff")
def update_status():
    _, airline_name = _get_staff_and_airline()

    if request.method == "POST":
        flight_num = request.form.get("flight_number")
        new_status = request.form.get("status")

        if not flight_num or not new_status:
            flash("Flight number and new status are required.")
            return redirect(url_for("staff.update_status"))

        # Use execute_sql for updates
        try:
            execute_sql("UPDATE flight SET status=%s WHERE airline_name=%s AND flight_number=%s",
                        (new_status, airline_name, flight_num))
            flash(f"Flight {flight_num} status updated to {new_status}.")
        except Exception as e:
            flash(f"Error updating status: {e}")

        return redirect(url_for("staff.update_status"))

    # GET: Show all upcoming/in-progress flights to allow selection
    sql = """
        SELECT * FROM flight
        WHERE airline_name = %s
        ORDER BY departure_time ASC
    """
    flights = query_all(sql, (airline_name,))
    return render_template("staff_operator_status.html", flights=flights, airline_name=airline_name)


@staff_bp.route("/api/get_customers")
@login_required(role="staff")
def get_customers():
    """Fetch customer emails for suggestions."""
    _, airline_name = _get_staff_and_airline()
    try:
        sql = """
            SELECT DISTINCT p.customer_email
            FROM purchases p
            JOIN ticket t ON p.ticket_ID = t.ticket_ID
            WHERE t.airline_name = %s
            ORDER BY p.purchase_date DESC
            LIMIT 200
        """
        customers = query_all(sql, (airline_name,))
        return jsonify([c['customer_email'] for c in customers])
    except Exception as e:
        return jsonify([])

@staff_bp.route("/api/get_airports")
@login_required(role="staff")
def get_airports():
    """
    Fetch distinct origins and destinations based on the current time filter.
    If range='all', show all airports used in any flight.
    If range='30' (default), show only airports used in flights in the next 30 days.
    """
    _, airline_name = _get_staff_and_airline()
    
    date_range = request.args.get("range", "30")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    # Base condition: Airline
    conditions = ["f.airline_name = %s"]
    params = [airline_name]

    # Time filtering logic (matches search_flights_api)
    if start_date or end_date:
        if start_date:
            conditions.append("f.departure_time >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("f.departure_time <= %s")
            params.append(end_date)
    elif date_range == "30":
        conditions.append("f.departure_time BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 30 DAY)")
    
    where_clause = " AND ".join(conditions)

    try:
        # Origins
        sql_origins = f"""
            SELECT DISTINCT f.departure_airport AS code, a.city
            FROM flight f
            JOIN airport a ON f.departure_airport = a.name
            WHERE {where_clause}
            ORDER BY a.city, f.departure_airport
        """
        origins = query_all(sql_origins, tuple(params))

        # Destinations
        sql_dests = f"""
            SELECT DISTINCT f.arrival_airport AS code, a.city
            FROM flight f
            JOIN airport a ON f.arrival_airport = a.name
            WHERE {where_clause}
            ORDER BY a.city, f.arrival_airport
        """
        dests = query_all(sql_dests, tuple(params))

        return jsonify({"origins": origins, "destinations": dests})
    except Exception as e:
        print(f"Error getting airports: {e}")
        return jsonify({"origins": [], "destinations": []})

@staff_bp.route("/api/search_flights")

@staff_bp.route("/api/search_flights")
@login_required(role="staff")
def search_flights_api():
    """API for dynamic flight search on dashboard."""
    _, airline_name = _get_staff_and_airline()
    
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    origin = request.args.get("origin")
    dest = request.args.get("destination")
    date_range = request.args.get("range", "30") # Default to 30 days
    
    params = [airline_name]
    conditions = ["f.airline_name = %s"]
    
    # 1. If specific dates are manually picked, they take priority
    if start_date or end_date:
        if start_date:
            conditions.append("f.departure_time >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("f.departure_time <= %s")
            params.append(end_date)
    else:
        # 2. Otherwise, use the toggle (30 days vs All)
        if date_range == "30":
            conditions.append("f.departure_time BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 30 DAY)")
        else:
            pass

    if origin:
        conditions.append("(f.departure_airport LIKE %s OR da.city LIKE %s)")
        params.extend([f"%{origin}%", f"%{origin}%"])
    if dest:
        conditions.append("(f.arrival_airport LIKE %s OR aa.city LIKE %s)")
        params.extend([f"%{dest}%", f"%{dest}%"])
        
    where_clause = " AND ".join(conditions)
    
    # Join with airport table to get city names
    sql = f"""
        SELECT f.*, da.city AS dep_city, aa.city AS arr_city
        FROM flight f
        LEFT JOIN airport da ON f.departure_airport = da.name
        LEFT JOIN airport aa ON f.arrival_airport = aa.name
        WHERE {where_clause}
        ORDER BY f.departure_time ASC
    """
    
    try:
        flights = query_all(sql, tuple(params))
        # Serialize datetime objects for JSON
        for f in flights:
            if f.get('departure_time'): 
                f['departure_time'] = f['departure_time'].strftime('%Y-%m-%d %H:%M')
            if f.get('arrival_time'): 
                f['arrival_time'] = f['arrival_time'].strftime('%Y-%m-%d %H:%M')
        return jsonify(flights)
    except Exception as e:
        print(f"Search API Error: {e}")
        return jsonify([])