from flask import Blueprint, render_template, request, session, flash, redirect, url_for, jsonify
from datetime import datetime, timedelta

from .utils import login_required, query_all, query_one, execute_sql

customer_bp = Blueprint("customer", __name__)

@customer_bp.route("/dashboard")
@login_required(role="customer")
def dashboard():
    """
    Main page: Booking interface (Search)
    """
    return render_template("customer_dashboard.html")

@customer_bp.route("/upcoming")
@login_required(role="customer")
def upcoming_flights():
    """
    Show upcoming purchased flights
    """
    email = session.get("user_id")
    sql = """
        SELECT f.*, t.ticket_ID, p.purchase_date,
               dep.city as dep_city, 
               arr.city as arr_city
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        LEFT JOIN airport dep ON f.departure_airport = dep.name
        LEFT JOIN airport arr ON f.arrival_airport = arr.name
        WHERE p.customer_email=%s AND f.status IN ('upcoming', 'Delayed')
        ORDER BY f.departure_time ASC
    """
    flights = query_all(sql, (email,))
    return render_template("customer_upcoming.html", flights=flights)


# --- NEW API FOR DYNAMIC SEARCH ---
@customer_bp.route("/api/search_flights")
@login_required(role="customer")
def search_flights_api():
    """
    API that returns JSON list of flights.
    If no params provided, returns ALL upcoming flights.
    """
    origin = request.args.get("origin", "").strip()
    destination = request.args.get("destination", "").strip()
    date = request.args.get("date", "").strip()

    # Base condition: Only show future flights that are not cancelled
    conditions = ["f.status = 'upcoming' AND f.departure_time > NOW()"]
    params = []

    if origin:
        conditions.append("(f.departure_airport = %s OR dep.city LIKE %s)")
        params.extend([origin, f"%{origin}%"])
    
    if destination:
        conditions.append("(f.arrival_airport = %s OR arr.city LIKE %s)")
        params.extend([destination, f"%{destination}%"])
    
    if date:
        conditions.append("DATE(f.departure_time) = %s")
        params.append(date)

    where_clause = " AND ".join(conditions)

    # Join with airport table to get City Names for display
    sql = f"""
    SELECT f.*, 
               dep.city as dep_city, 
               arr.city as arr_city
        FROM flight f
        LEFT JOIN airport dep ON f.departure_airport = dep.name
        LEFT JOIN airport arr ON f.arrival_airport = arr.name
        WHERE {where_clause}
        ORDER BY f.departure_time ASC
        LIMIT 50
    """
    
    try:
        flights = query_all(sql, tuple(params))
        # Convert datetime objects to string for JSON serialization
        for f in flights:
            if isinstance(f.get('departure_time'), datetime):
                f['departure_time'] = f['departure_time'].strftime('%Y-%m-%d %H:%M')
            if isinstance(f.get('arrival_time'), datetime):
                f['arrival_time'] = f['arrival_time'].strftime('%Y-%m-%d %H:%M')
            # Decimal to float/str if needed, though simplejson usually handles it. 
            # If using standard json, might need conversion.
            if 'price' in f:
                f['price'] = str(f['price'])

        return jsonify(flights)
    except Exception as e:
        print(f"Error in search_flights_api: {e}")
        return jsonify({"error": str(e)}), 500
    

@customer_bp.route("/api/active_airports")
@login_required(role="customer")
def get_active_airports():
    """
    Return airports that actually have upcoming flights.
    Used for autocomplete to only show relevant airports.
    """
    # Get origins (airports with departing flights)
    sql_origins = """
        SELECT DISTINCT f.departure_airport as code, a.city
        FROM flight f
        JOIN airport a ON f.departure_airport = a.name
        WHERE f.status = 'upcoming' AND f.departure_time > NOW()
        ORDER BY a.city
    """
    origins = query_all(sql_origins)

    # Get destinations (airports with arriving flights)
    sql_dests = """
        SELECT DISTINCT f.arrival_airport as code, a.city
        FROM flight f
        JOIN airport a ON f.arrival_airport = a.name
        WHERE f.status = 'upcoming' AND f.departure_time > NOW()
        ORDER BY a.city
    """
    dests = query_all(sql_dests)

    return jsonify({
        "origins": origins,
        "destinations": dests
    })


@customer_bp.route("/flights", methods=["GET", "POST"])
@login_required(role="customer")
def flights():
    """
    过滤已购航班：date range, origin, dest
    """
    email = session.get("user_id")
    flights = []
    if request.method == "POST":
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()
        origin = request.form.get("origin", "").strip()
        destination = request.form.get("destination", "").strip()

        conditions = ["p.customer_email=%s"]
        params = [email]

        if start_date:
            conditions.append("DATE(f.departure_time) >= %s")
            params.append(start_date)
        if end_date:
            conditions.append("DATE(f.departure_time) <= %s")
            params.append(end_date)

        if origin:
            conditions.append("f.departure_airport=%s")
            params.append(origin)
        if destination:
            conditions.append("f.arrival_airport=%s")
            params.append(destination)

        where_clause = " AND ".join(conditions)
        sql = f"""
            SELECT f.*, t.ticket_ID, p.purchase_date
            FROM purchases p
            JOIN ticket t ON p.ticket_ID = t.ticket_ID
            JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
            WHERE {where_clause}
            ORDER BY f.departure_time DESC
        """
        flights = query_all(sql, tuple(params))

    return render_template("customer_flights.html", flights=flights)


@customer_bp.route("/search", methods=["GET", "POST"])
@login_required(role="customer")
def search():
    """
    客户搜索航班 + purchase (Fallback page)
    """
    origin = request.args.get("origin") or request.form.get("origin")
    destination = request.args.get("destination") or request.form.get("destination")
    date = request.args.get("date") or request.form.get("date")

    conditions = ["f.status='upcoming'"]
    params = []

    if date:
        conditions.append("DATE(f.departure_time) = %s")
        params.append(date)
    
    if origin:
        conditions.append("f.departure_airport=%s")
        params.append(origin)
    if destination:
        conditions.append("f.arrival_airport=%s")
        params.append(destination)

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT f.*
        FROM flight f
        WHERE {where_clause}
        ORDER BY f.departure_time ASC
    """
    flights = query_all(sql, tuple(params))

    return render_template("customer_search.html", flights=flights)

@customer_bp.route("/book_ticket", methods=["GET"])
@login_required(role="customer")
def book_ticket():
    """
    Render the 'Buy Ticket Only' page for a specific flight.
    """
    airline = request.args.get("airline")
    flight_num = request.args.get("flight_number")
    
    if not airline or not flight_num:
        flash("Invalid flight selection.", "danger")
        return redirect(url_for("customer.dashboard"))

    # Updated SQL to join with airport table for city names
    sql = """
        SELECT f.*, 
               dep.city as dep_city, 
               arr.city as arr_city
        FROM flight f
        LEFT JOIN airport dep ON f.departure_airport = dep.name
        LEFT JOIN airport arr ON f.arrival_airport = arr.name
        WHERE f.airline_name=%s AND f.flight_number=%s
    """
    flight = query_one(sql, (airline, flight_num))
    
    if not flight:
        flash("Flight not found.", "danger")
        return redirect(url_for("customer.dashboard"))

    return render_template("customer_booking.html", flight=flight)


def check_capacity(airline_name, flight_number):
    """
    检查 flight 剩余座位
    """
    sql_airplane = """
        SELECT a.seat_capacity
        FROM flight f
        JOIN airplane a ON f.airplane_assigned = a.airplane_id
            AND f.airline_name = a.airline_name
        WHERE f.airline_name=%s AND f.flight_number=%s
    """
    row = query_one(sql_airplane, (airline_name, flight_number))
    if not row:
        return False, "Flight not found."
    capacity = row["seat_capacity"]

    sql_sold = """
        SELECT COUNT(*) AS cnt
        FROM ticket t
        WHERE t.airline_name=%s AND t.flight_number=%s
    """
    sold = query_one(sql_sold, (airline_name, flight_number))["cnt"]

    if sold >= capacity:
        return False, "No available seats."
    return True, ""


@customer_bp.route("/purchase", methods=["POST"])
@login_required(role="customer")
def purchase():
    """
    客户购票
    """
    email = session.get("user_id")
    airline_name = request.form.get("airline_name")
    flight_number = request.form.get("flight_number")

    ok, msg = check_capacity(airline_name, flight_number)
    if not ok:
        flash(msg)
        return redirect(url_for("customer.dashboard"))

    flight = query_one(
        "SELECT price FROM flight WHERE airline_name=%s AND flight_number=%s",
        (airline_name, flight_number),
    )
    if not flight:
        flash("Flight not found.")
        return redirect(url_for("customer.dashboard"))

    price = flight["price"]
    ticket_id = datetime.now().strftime("%Y%m%d%H%M%S") + "C"

    try:
        execute_sql(
            """
            INSERT INTO ticket (ticket_ID, ticket_price, ticket_status, airline_name, flight_number)
            VALUES (%s, %s, 'Confirmed', %s, %s)
            """,
            (ticket_id, price, airline_name, flight_number),
        )

        execute_sql(
            """
            INSERT INTO purchases (customer_email, agent_email, ticket_ID, purchase_date)
            VALUES (%s, NULL, %s, NOW())
            """,
            (email, ticket_id),
        )
        flash("Ticket purchased successfully.")
    except Exception as e:
        flash(f"Purchase failed: {e}")

    return redirect(url_for("customer.dashboard"))


@customer_bp.route("/spending", methods=["GET", "POST"])
@login_required(role="customer")
def spending():
    email = session.get("user_id")
    custom = False
    start_date = None
    end_date = None

    if request.method == "POST":
        custom = True
        start_date = request.form.get("start_date", "").strip()
        end_date = request.form.get("end_date", "").strip()

    if not custom:
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=365)

    sql_total = """
        SELECT COALESCE(SUM(t.ticket_price), 0) AS total
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        WHERE p.customer_email=%s
          AND DATE(p.purchase_date) BETWEEN %s AND %s
    """
    total_row = query_one(sql_total, (email, start_date, end_date))
    total_spending = float(total_row["total"]) if total_row else 0.0

    sql_month = """
        SELECT DATE_FORMAT(p.purchase_date, '%%Y-%%m') AS month,
               COALESCE(SUM(t.ticket_price), 0) AS total
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        WHERE p.customer_email=%s
          AND DATE(p.purchase_date) BETWEEN %s AND %s
        GROUP BY month
        ORDER BY month
    """
    rows = query_all(sql_month, (email, start_date, end_date))
    months = [r["month"] for r in rows]
    amounts = [float(r["total"]) for r in rows]

    return render_template(
        "customer_spending.html",
        total_spending=total_spending,
        months=months,
        amounts=amounts,
        start_date=start_date,
        end_date=end_date,
    )