from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from .utils import query_one, execute_sql

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    注册：可以选择 customer / agent / staff
    密码后端校验，两次一致才写入数据库（使用 hash）
    """
    if request.method == "POST":
        role = request.form.get("role")  # 'customer' / 'agent' / 'staff'
        email_or_username = request.form.get("email_or_username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not role or not email_or_username or not password:
            flash("All fields are required.")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.")
            return render_template("register.html")
        password_hash = generate_password_hash(password, method="pbkdf2:sha256:200000")

        try:
            if role == "customer":
                # 最简单版本：只收 email + password + name，其他信息先写死 / 或后续 profile 页面补充
                name = request.form.get("name", "").strip()
                if not name:
                    flash("Name is required for customer.")
                    return render_template("register.html")

                # 检查是否已存在
                existing = query_one("SELECT * FROM customer WHERE email=%s", (email_or_username,))
                if existing:
                    flash("Customer already exists.")
                    return render_template("register.html")

                # 这里为了满足 schema，填一些 demo 数据；正式项目应让用户完整填
                execute_sql(
                    """
                    INSERT INTO customer
                    (email, password, name, building_number, street, city, state,
                     phone_number, passport_expiration_date, passport_country, date_of_birth)
                    VALUES (%s, %s, %s, 0, '', '', '', '0000000000', '2099-12-31', 'N/A', '2000-01-01')
                    """,
                    (email_or_username, password_hash, name),
                )

            elif role == "agent":
                existing = query_one("SELECT * FROM booking_agent WHERE email=%s", (email_or_username,))
                if existing:
                    flash("Booking agent already exists.")
                    return render_template("register.html")

                execute_sql(
                    "INSERT INTO booking_agent (email, password) VALUES (%s, %s)",
                    (email_or_username, password_hash),
                )

            elif role == "staff":
                # staff 用 username
                first_name = request.form.get("first_name", "").strip()
                last_name = request.form.get("last_name", "").strip()
                airline_name = request.form.get("airline_name", "").strip()
                if not first_name or not last_name or not airline_name:
                    flash("Staff requires first name, last name and airline.")
                    return render_template("register.html")

                existing = query_one("SELECT * FROM staff WHERE username=%s", (email_or_username,))
                if existing:
                    flash("Staff already exists.")
                    return render_template("register.html")

                execute_sql(
                    """
                    INSERT INTO staff
                    (username, password, first_name, last_name, date_of_birth, airline_name)
                    VALUES (%s, %s, %s, %s, '1990-01-01', %s)
                    """,
                    (email_or_username, password_hash, first_name, last_name, airline_name),
                )
            else:
                flash("Invalid role.")
                return render_template("register.html")

            flash("Register success, please login.")
            return redirect(url_for("auth.login"))

        except Exception as e:
            flash(f"Error during registration: {e}")
            return render_template("register.html")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    登录：根据选择的角色在对应表里检查密码
    """
    if request.method == "POST":
        role = request.form.get("role")
        email_or_username = request.form.get("email_or_username", "").strip()
        password = request.form.get("password", "")

        if not role or not email_or_username or not password:
            flash("All fields are required.")
            return render_template("login.html")

        user = None
        display_name = ""
        permissions = []

        try:
            if role == "customer":
                user = query_one("SELECT * FROM customer WHERE email=%s", (email_or_username,))
            
                if user:
                    display_name = user.get("name", user["email"])
            elif role == "agent":
                user = query_one("SELECT * FROM booking_agent WHERE email=%s", (email_or_username,))
                if user:
                    display_name = user["email"]
            elif role == "staff":
                user = query_one("SELECT * FROM staff WHERE username=%s", (email_or_username,))
                if user:
                    display_name = f"{user['first_name']} {user['last_name']}"

                    # staff-specific: load permissions
                    perms_rows = query_one_permissions(email_or_username)
                    permissions = perms_rows

                    session["airline_name"] = user["airline_name"]
            else:
                flash("Invalid role.")
                return render_template("login.html")

            if not user:
                flash("User not found.")
                return render_template("login.html")
            
            # # no hash, just for testing
            # if user["password"] != password:
            #     flash("Invalid password.")
            #     return render_template("login.html")
            if not check_password_hash(user["password"], password):
                flash("Invalid password.")
                return render_template("login.html")

            session.clear()
            session["user_role"] = role
            session["user_id"] = email_or_username
            session["display_name"] = display_name
            if permissions:
                session["permissions"] = permissions

            if role == "staff":
                session["airline_name"] = user["airline_name"]

            flash("Login success.")
            if role == "customer":
                return redirect(url_for("customer.dashboard"))
            elif role == "agent":
                return redirect(url_for("agent.dashboard"))
            else:
                return redirect(url_for("staff.dashboard"))

        except Exception as e:
            flash(f"Login error: {e}")
            return render_template("login.html")

    return render_template("login.html")


def query_one_permissions(username):
    """
    查询 staff 权限列表
    """
    from .utils import query_all
    rows = query_all("SELECT permission_type FROM permission WHERE username=%s", (username,))
    return [r["permission_type"] for r in rows] if rows else []


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.")
    return redirect(url_for("index"))
