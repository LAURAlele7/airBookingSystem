from flask import Blueprint, render_template, request, current_app, jsonify, flash
from .utils import query_all, query_one
import pymysql

public_bp = Blueprint("public", __name__)

@public_bp.route("/search", methods=["GET", "POST"])
def search():
    """
    Public user search for upcoming flights.
    """
    # This route renders the main search page (index.html)
    # The actual searching is done via the /api/live_search endpoint called by JS
    return render_template("index.html")


@public_bp.route("/status_page")
def status_page():
    """Render the dedicated status check page."""
    return render_template("public_status.html")


@public_bp.route("/api/get_airports")
def get_airports():
    """Return distinct origins and destinations with city names based on UPCOMING flights."""
    try:
        # Get distinct departure airports ONLY from upcoming flights
        sql_origins = """
            SELECT DISTINCT f.departure_airport AS code, a.city
            FROM flight f
            JOIN airport a ON f.departure_airport = a.name
            WHERE f.status = 'upcoming' AND f.departure_time > NOW()
            ORDER BY a.city
        """
        origins = query_all(sql_origins)

        # Get distinct arrival airports ONLY from upcoming flights
        sql_dests = """
            SELECT DISTINCT f.arrival_airport AS code, a.city
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
    except Exception as e:
        print(f"Error fetching airports: {e}")
        return jsonify({"origins": [], "destinations": []})


@public_bp.route("/api/live_search")
def live_search():
    """Search flights dynamically using query_all."""
    origin = request.args.get("origin", "").strip()
    destination = request.args.get("destination", "").strip()
    date = request.args.get("date", "").strip()

    # Base query: Join with airport table to allow searching by City Name as well as Airport Code
    query = """
        SELECT f.*, da.city AS dep_city, aa.city AS arr_city
        FROM flight f
        JOIN airport da ON f.departure_airport = da.name
        JOIN airport aa ON f.arrival_airport = aa.name
        WHERE f.status = 'upcoming' AND f.departure_time > NOW()
    """
    params = []

    if origin:
        query += " AND (f.departure_airport LIKE %s OR da.city LIKE %s OR da.city IN (SELECT ca.city_name FROM city_alias ca WHERE ca.alias_name = %s))"
        params.extend([f"%{origin}%", f"%{origin}%"], origin)
    if destination:
        query += " AND (f.arrival_airport LIKE %s OR aa.city LIKE %s OR aa.city IN (SELECT ca.city_name FROM city_alias ca WHERE ca.alias_name = %s))"
        params.extend([f"%{destination}%", f"%{destination}%", destination])
    if date:
        query += " AND DATE(f.departure_time) = %s"
        params.append(date)
    
    query += " ORDER BY f.departure_time ASC LIMIT 50"

    try:
        flights = query_all(query, tuple(params))
        
        # Convert datetime objects to string for JSON serialization
        for f in flights:
            if f.get('departure_time'):
                f['departure_time'] = str(f['departure_time'])
            if f.get('arrival_time'):
                f['arrival_time'] = str(f['arrival_time'])
            if 'price' in f:
                f['price'] = str(f['price'])
                
        return jsonify(flights)
    except Exception as e:
        print(f"Error in live search: {e}")
        return jsonify([])


@public_bp.route("/api/check_status")
def check_status_api():
    """
    API for dynamic status checking.
    Filters by airline, flight number, or date.
    """
    airline = request.args.get("airline", "").strip()
    flight_num = request.args.get("flight_number", "").strip()
    date = request.args.get("date", "").strip()

    # Base query for active flights (in-progress or delayed)
    sql = """
        SELECT f.*, da.city AS dep_city, aa.city AS arr_city
        FROM flight f
        JOIN airport da ON f.departure_airport = da.name
        JOIN airport aa ON f.arrival_airport = aa.name
        WHERE f.status IN ('in-progress', 'delayed')
    """
    params = []

    if airline:
        sql += " AND f.airline_name LIKE %s"
        params.append(f"%{airline}%")
    
    if flight_num:
        sql += " AND f.flight_number LIKE %s"
        params.append(f"%{flight_num}%")
        
    if date:
        sql += " AND DATE(f.departure_time) = %s"
        params.append(date)

    sql += " ORDER BY f.departure_time DESC LIMIT 20"

    try:
        flights = query_all(sql, tuple(params))
        # Serialization
        for f in flights:
            if f.get('departure_time'): f['departure_time'] = str(f['departure_time'])
            if f.get('arrival_time'): f['arrival_time'] = str(f['arrival_time'])
            if 'price' in f: f['price'] = str(f['price'])
        return jsonify(flights)
    except Exception as e:
        print(f"Error in status API: {e}")
        return jsonify([])