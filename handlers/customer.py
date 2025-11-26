from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from datetime import datetime, timedelta

from .utils import login_required, query_all, query_one, execute_sql

customer_bp = Blueprint("customer", __name__)

@customer_bp.route("/dashboard")
@login_required(role="customer")
def dashboard():
    """
    默认：展示 upcoming purchased flights
    """
    email = session.get("user_id")
    sql = """
        SELECT f.*, t.ticket_ID, p.purchase_date
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE p.customer_email=%s AND f.departure_time >= NOW()
        ORDER BY f.departure_time ASC
    """
    flights = query_all(sql, (email,))
    return render_template("customer_dashboard.html", flights=flights)


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
    客户搜索航班 + purchase
    """
    flights = []
    if request.method == "POST":
        origin = request.form.get("origin", "").strip()
        destination = request.form.get("destination", "").strip()
        date = request.form.get("date", "").strip()

        if not date:
            flash("Date is required.")
        else:
            conditions = ["DATE(f.departure_time) = %s", "f.status='upcoming'"]
            params = [date]

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
            """
            flights = query_all(sql, tuple(params))

    return render_template("customer_search.html", flights=flights)


def check_capacity(airline_name, flight_number):
    """
    检查 flight 剩余座位
    """
    # 获取当前飞机 seat capacity
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

    # 当前已卖票数量
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
    客户购票：server side enforce capacity & pricing
    """
    email = session.get("user_id")
    airline_name = request.form.get("airline_name")
    flight_number = request.form.get("flight_number")

    ok, msg = check_capacity(airline_name, flight_number)
    if not ok:
        flash(msg)
        return redirect(url_for("customer.search"))

    # 获取 flight price
    flight = query_one(
        "SELECT price FROM flight WHERE airline_name=%s AND flight_number=%s",
        (airline_name, flight_number),
    )
    if not flight:
        flash("Flight not found.")
        return redirect(url_for("customer.search"))

    price = flight["price"]

    # 创建 ticket_ID 简单一点：时间戳 + email hash 片段（实际项目用更安全/唯一生成）
    ticket_id = datetime.now().strftime("%Y%m%d%H%M%S") + "C"

    try:
        # 插入 ticket
        execute_sql(
            """
            INSERT INTO ticket (ticket_ID, ticket_price, ticket_status, airline_name, flight_number)
            VALUES (%s, %s, 'Confirmed', %s, %s)
            """,
            (ticket_id, price, airline_name, flight_number),
        )

        # 插入 purchases (无 agent)
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
    """
    默认：过去 12 个月总消费 + 过去 6 个月 bar chart
    自定义：date range，总消费 + month-by-month bar chart
    """
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

    # Total spending
    sql_total = """
        SELECT COALESCE(SUM(t.ticket_price), 0) AS total
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        WHERE p.customer_email=%s
          AND DATE(p.purchase_date) BETWEEN %s AND %s
    """
    total_row = query_one(sql_total, (email, start_date, end_date))
    total_spending = float(total_row["total"]) if total_row else 0.0

    # Month by month
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
