from flask import Blueprint, render_template, request, flash
from .utils import query_all, query_one

public_bp = Blueprint("public", __name__)

@public_bp.route("/search", methods=["GET", "POST"])
def search():
    """
    公共用户搜索 upcoming flights:
    - origin / destination airport code
    - 或 city（包含 alias）
    - date
    """
    flights = []
    if request.method == "POST":
        origin = request.form.get("origin", "").strip()
        destination = request.form.get("destination", "").strip()
        date = request.form.get("date", "").strip()

        if not date:
            flash("Date is required.")
        else:
            params = []
            conditions = ["DATE(f.departure_time) = %s", "f.status = 'upcoming'"]
            params.append(date)

            # origin / destination 可以是 airport code 或 city（含 alias）
            if origin:
                conditions.append(
                    "(f.departure_airport IN (SELECT name FROM airport WHERE city=%s) "
                    "OR f.departure_airport = %s "
                    "OR f.departure_airport IN (SELECT a.name FROM airport a "
                    "JOIN city_alias ca ON a.city=ca.city_name WHERE ca.alias_name=%s))"
                )
                params.extend([origin, origin, origin])

            if destination:
                conditions.append(
                    "(f.arrival_airport IN (SELECT name FROM airport WHERE city=%s) "
                    "OR f.arrival_airport = %s "
                    "OR f.arrival_airport IN (SELECT a.name FROM airport a "
                    "JOIN city_alias ca ON a.city=ca.city_name WHERE ca.alias_name=%s))"
                )
                params.extend([destination, destination, destination])

            where_clause = " AND ".join(conditions)
            sql = f"""
                SELECT f.*, da.city AS dep_city, aa.city AS arr_city
                FROM flight f
                JOIN airport da ON f.departure_airport = da.name
                JOIN airport aa ON f.arrival_airport = aa.name
                WHERE {where_clause}
            """
            flights = query_all(sql, tuple(params))

    return render_template("index.html", flights=flights)


@public_bp.route("/status", methods=["GET", "POST"])
def status():
    """
    查询 in-progress flights 状态（根据 airline_name + flight_number）
    """
    flight = None
    if request.method == "POST":
        airline_name = request.form.get("airline_name", "").strip()
        flight_number = request.form.get("flight_number", "").strip()
        if not airline_name or not flight_number:
            flash("Airline and flight number are required.")
        else:
            sql = """
                SELECT * FROM flight
                WHERE airline_name=%s AND flight_number=%s AND status='in-progress'
            """
            flight = query_one(sql, (airline_name, flight_number))
            if not flight:
                flash("No in-progress flight found with given info.")
    return render_template("index.html", status_flight=flight)
