import os
from flask import Flask, render_template, redirect, url_for, session
from dotenv import load_dotenv
from datetime import datetime

from handlers.auth_handlers import auth_bp
from handlers.public import public_bp
from handlers.customer import customer_bp
from handlers.agent import agent_bp
from handlers.staff import staff_bp
from handlers.utils import init_db_connection, login_required

load_dotenv()

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    # Secret key & DB
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev_secret_key")
    app.config["DB_HOST"] = os.getenv("DB_HOST", "localhost")
    app.config["DB_PORT"] = int(os.getenv("DB_PORT", "3306"))
    app.config["DB_USER"] = os.getenv("DB_USER", "root")
    app.config["DB_PASSWORD"] = os.getenv("DB_PASSWORD", "")
    app.config["DB_NAME"] = os.getenv("DB_NAME", "bookingsystem")

    init_db_connection(app)

    def datetimeformat(value, format='%Y-%m-%d %H:%M'):
            """Jinja 过滤器：格式化 datetime 对象"""
            if value is None:
                return ""
            try:
                # 确保 value 是一个 datetime 对象
                return value.strftime(format)
            except AttributeError:
                # 如果不是，则返回其字符串表示
                return str(value)

    app.jinja_env.filters['datetimeformat'] = datetimeformat

    # 注册蓝图
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp, url_prefix="/customer")
    app.register_blueprint(agent_bp, url_prefix="/agent")
    app.register_blueprint(staff_bp, url_prefix="/staff")

    @app.route("/")
    def index():
        # 未登录就看公共首页
        if "user_role" not in session:
            return render_template("index.html")
        # 登录后根据角色进入 dashboard
        role = session.get("user_role")
        if role == "customer":
            return redirect(url_for("customer.dashboard"))
        elif role == "agent":
            return redirect(url_for("agent.dashboard"))
        elif role == "staff":
            return redirect(url_for("staff.dashboard"))
        else:
            return render_template("index.html")

    # 示例：通用 dashboard 路由（如果老师一定要求这个形式）
    @app.route("/dashboard")
    @login_required()
    def dashboard():
        role = session.get("user_role")
        if role == "customer":
            return redirect(url_for("customer.dashboard"))
        elif role == "agent":
            return redirect(url_for("agent.dashboard"))
        elif role == "staff":
            return redirect(url_for("staff.dashboard"))
        return redirect(url_for("index"))

    return app


if __name__ == "__main__":
    app = create_app()
    # 在 XAMPP / Windows 下开发用这个就好
    app.run(host="127.0.0.1", port=5000, debug=True)
