import pymysql
from flask import current_app, g, redirect, url_for, session, flash
from functools import wraps

def get_db():
    """
    获取当前请求使用的 DB 连接，存在 g 中以复用。
    """
    if "db" not in g:
        g.db = pymysql.connect(
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            database=current_app.config["DB_NAME"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            charset="utf8mb4",
        )
    return g.db

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db_connection(app):
    app.teardown_appcontext(close_db)

def login_required(role=None):
    """
    装饰器：需要登录。
    role 可选：'customer', 'agent', 'staff'
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_role" not in session:
                flash("Please login first.")
                return redirect(url_for("auth.login"))

            if role is not None and session.get("user_role") != role:
                flash("You are not authorized to access this page.")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

def staff_permission_required(permission_type):
    """
    staff 权限检查：'Admin' 或 'Operator'
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("user_role") != "staff":
                flash("Staff only.")
                return redirect(url_for("index"))

            perms = session.get("permissions", [])
            if permission_type not in perms:
                flash("You don't have required permission.")
                return redirect(url_for("staff.dashboard"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

def query_one(sql, params=None):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchone()

def query_all(sql, params=None):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchall()

def execute_sql(sql, params=None):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(sql, params or ())
    # autocommit = True
