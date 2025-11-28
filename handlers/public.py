from flask import Blueprint, render_template, request, current_app, jsonify, flash
from .utils import query_all, query_one
import pymysql

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


@public_bp.route("/api/get_airports")
def get_airports():
    """Fetch distinct airports for the suggestion boxes using query_all."""
    try:
        query = """
            SELECT DISTINCT departure_airport as code FROM flight
            UNION
            SELECT DISTINCT arrival_airport as code FROM flight
        """
        results = query_all(query)
        # Assuming query_all returns a list of dictionaries
        return jsonify([r['code'] for r in results])
    except Exception as e:
        print(f"Error fetching airports: {e}")
        return jsonify([])

from flask import Blueprint, render_template, request, current_app, jsonify, flash
from .utils import query_all, query_one
import pymysql

public_bp = Blueprint("public", __name__)

@public_bp.route("/search", methods=["GET", "POST"])
def search():
    """
    Public user search for upcoming flights.
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
    Check in-progress flight status.
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


@public_bp.route("/api/get_airports")
def get_airports():
    """Fetch distinct airports for the suggestion boxes using query_all."""
    try:
        query = """
            SELECT DISTINCT departure_airport as code FROM flight
            UNION
            SELECT DISTINCT arrival_airport as code FROM flight
        """
        results = query_all(query)
        # Assuming query_all returns a list of dictionaries
        return jsonify([r['code'] for r in results])
    except Exception as e:
        print(f"Error fetching airports: {e}")
        return jsonify([])


@public_bp.route("/api/live_search")
def live_search():
    """Search flights dynamically using query_all."""
    origin = request.args.get("origin", "").strip()
    destination = request.args.get("destination", "").strip()
    date = request.args.get("date", "").strip()

    # We join with the airport table to allow searching by City Name as well as Airport Code
    query = """
        SELECT f.*, da.city AS dep_city, aa.city AS arr_city
        FROM flight f
        JOIN airport da ON f.departure_airport = da.name
        JOIN airport aa ON f.arrival_airport = aa.name
        WHERE 1=1
    """
    params = []

    if origin:
        query += " AND (f.departure_airport LIKE %s OR da.city LIKE %s)"
        params.extend([f"%{origin}%", f"%{origin}%"])
    if destination:
        query += " AND (f.arrival_airport LIKE %s OR aa.city LIKE %s)"
        params.extend([f"%{destination}%", f"%{destination}%"])
    if date:
        query += " AND DATE(f.departure_time) = %s"
        params.append(date)
    
    query += " ORDER BY f.departure_time ASC LIMIT 20"

    try:
        flights = query_all(query, tuple(params))
        
        # Convert datetime objects to string for JSON serialization
        for f in flights:
            if f.get('departure_time'):
                f['departure_time'] = str(f['departure_time'])
            if f.get('arrival_time'):
                f['arrival_time'] = str(f['arrival_time'])
                
        return jsonify(flights)
    except Exception as e:
        print(f"Error in live search: {e}")
        return jsonify([])