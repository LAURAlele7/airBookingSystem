from flask import Blueprint, render_template, request, session, flash, redirect, url_for
from datetime import datetime, timedelta

from .utils import login_required, query_all, query_one, execute_sql
from .customer import check_capacity  # 复用容量检查

agent_bp = Blueprint("agent", __name__)

@agent_bp.route("/dashboard")
@login_required(role="agent")
def dashboard():
    """
    agent 查看近期他帮客户购买的航班
    """
    email = session.get("user_id")
    sql = """
        SELECT f.*, t.ticket_ID, p.customer_email, p.purchase_date
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        JOIN flight f ON t.airline_name = f.airline_name AND t.flight_number = f.flight_number
        WHERE p.agent_email=%s
        ORDER BY p.purchase_date DESC
        LIMIT 20
    """
    flights = query_all(sql, (email,))
    return render_template("agent_dashboard.html", flights=flights)


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


@agent_bp.route("/search", methods=["GET", "POST"])
@login_required(role="agent")
def search():
    """
    agent 搜索航班，但仅限自己 work_with 表中 airlines
    """
    email = session.get("user_id")
    flights = []

    # 先查 agent 可操作的 airlines
    airlines = query_all(
        "SELECT airline_name FROM work_with WHERE agent_email=%s",
        (email,),
    )
    allowed = [a["airline_name"] for a in airlines]

    if request.method == "POST":
        origin = request.form.get("origin", "").strip()
        destination = request.form.get("destination", "").strip()
        date = request.form.get("date", "").strip()

        if not date:
            flash("Date is required.")
        else:
            if not allowed:
                flash("You are not associated with any airline.")
            else:
                conditions = [
                    "DATE(f.departure_time) = %s",
                    "f.status='upcoming'",
                    "f.airline_name IN ({})".format(
                        ",".join(["%s"] * len(allowed))
                    )
                ]
                params = [date] + allowed

                if origin:
                    conditions.append("f.departure_airport=%s")
                    params.append(origin)
                if destination:
                    conditions.append("f.arrival_airport=%s")
                    params.append(destination)

                where_clause = " AND ".join(conditions)
                sql = f"SELECT f.* FROM flight f WHERE {where_clause}"
                flights = query_all(sql, tuple(params))

    return render_template("agent_search.html", flights=flights)


@agent_bp.route("/purchase", methods=["POST"])
@login_required(role="agent")
def purchase():
    """
    agent 代表 customer 购票
    """
    agent_email = session.get("user_id")
    customer_email = request.form.get("customer_email", "").strip()
    airline_name = request.form.get("airline_name")
    flight_number = request.form.get("flight_number")

    if not customer_email:
        flash("Customer email is required.")
        return redirect(url_for("agent.search"))

    # 确认 customer 存在
    cust = query_one("SELECT * FROM customer WHERE email=%s", (customer_email,))
    if not cust:
        flash("Customer not found.")
        return redirect(url_for("agent.search"))

    # 确认 agent 和 airline work_with
    rel = query_one(
        "SELECT * FROM work_with WHERE agent_email=%s AND airline_name=%s",
        (agent_email, airline_name),
    )
    if not rel:
        flash("You are not allowed to sell tickets for this airline.")
        return redirect(url_for("agent.search"))

    ok, msg = check_capacity(airline_name, flight_number)
    if not ok:
        flash(msg)
        return redirect(url_for("agent.search"))

    flight = query_one(
        "SELECT price FROM flight WHERE airline_name=%s AND flight_number=%s",
        (airline_name, flight_number),
    )
    if not flight:
        flash("Flight not found.")
        return redirect(url_for("agent.search"))

    price = flight["price"]
    ticket_id = datetime.now().strftime("%Y%m%d%H%M%S") + "A"

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
            VALUES (%s, %s, %s, NOW())
            """,
            (customer_email, agent_email, ticket_id),
        )
        flash("Ticket purchased successfully.")
    except Exception as e:
        flash(f"Purchase failed: {e}")

    return redirect(url_for("agent.dashboard"))


@agent_bp.route("/analytics")
@login_required(role="agent")
def analytics():
    """
    统计：
    - 最近 30 天总佣金 / 平均佣金 / 卖出数量
    - Top 5 customers by ticket count (last 6 months)
    - Top 5 customers by commission (last year)
    """
    agent_email = session.get("user_id")

    # 最近 30 天
    sql_30 = """
        SELECT
            COALESCE(SUM(t.ticket_price*0.1), 0) AS total_commission,
            COALESCE(AVG(t.ticket_price*0.1), 0) AS avg_commission,
            COUNT(*) AS ticket_count
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        WHERE p.agent_email=%s
          AND p.purchase_date >= NOW() - INTERVAL 30 DAY
    """
    row_30 = query_one(sql_30, (agent_email,))
    total_commission = float(row_30["total_commission"])
    avg_commission = float(row_30["avg_commission"])
    ticket_count = int(row_30["ticket_count"])

    # Top 5 by ticket count (last 6 months)
    sql_top_tickets = """
        SELECT p.customer_email,
               COUNT(*) AS cnt
        FROM purchases p
        WHERE p.agent_email=%s
          AND p.purchase_date >= NOW() - INTERVAL 6 MONTH
        GROUP BY p.customer_email
        ORDER BY cnt DESC
        LIMIT 5
    """
    top_by_tickets = query_all(sql_top_tickets, (agent_email,))

    # Top 5 by commission (last year)
    sql_top_commission = """
        SELECT p.customer_email,
               COALESCE(SUM(t.ticket_price*0.1), 0) AS commission
        FROM purchases p
        JOIN ticket t ON p.ticket_ID = t.ticket_ID
        WHERE p.agent_email=%s
          AND p.purchase_date >= NOW() - INTERVAL 1 YEAR
        GROUP BY p.customer_email
        ORDER BY commission DESC
        LIMIT 5
    """
    top_by_commission = query_all(sql_top_commission, (agent_email,))

    # 为 bar chart 准备数组
    ticket_customers = [r["customer_email"] for r in top_by_tickets]
    ticket_counts = [int(r["cnt"]) for r in top_by_tickets]

    commission_customers = [r["customer_email"] for r in top_by_commission]
    commissions = [float(r["commission"]) for r in top_by_commission]

    return render_template(
        "agent_analytics.html",
        total_commission=total_commission,
        avg_commission=avg_commission,
        ticket_count=ticket_count,
        ticket_customers=ticket_customers,
        ticket_counts=ticket_counts,
        commission_customers=commission_customers,
        commissions=commissions,
    )
