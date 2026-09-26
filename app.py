from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "HBL_TOKEN_SYSTEM_SECRET"

DATABASE = "database.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db()

    # Employee table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            employee_name TEXT NOT NULL,
            department TEXT,
            lunch_count INTEGER DEFAULT 0,
            tiffen_count INTEGER DEFAULT 0,
            tea_count INTEGER DEFAULT 0
        )
    """)

    # Token records table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS token_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT NOT NULL,
            token_type TEXT NOT NULL,
            token_date TEXT NOT NULL,
            token_time TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return redirect(url_for("login"))


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        login_type = request.form.get("login_type")

        # -------------------------------------------------
        # EMPLOYEE LOGIN
        # -------------------------------------------------

        if login_type == "employee":

            employee_id = request.form.get("employee_id")
            employee_name = request.form.get("employee_name")

            conn = get_db()

            employee = conn.execute("""
                SELECT *
                FROM employees
                WHERE employee_id = ?
                AND LOWER(employee_name) = LOWER(?)
            """, (
                employee_id,
                employee_name
            )).fetchone()

            conn.close()

            if employee:

                session["employee_id"] = employee["employee_id"]
                session["employee_name"] = employee["employee_name"]

                return redirect(
                    url_for("employee_dashboard")
                )

            flash(
                "Invalid Employee ID or Employee Name",
                "danger"
            )

        # -------------------------------------------------
        # ADMIN LOGIN
        # -------------------------------------------------

        elif login_type == "admin":

            username = request.form.get("username")
            password = request.form.get("password")

            if (
                username == "HBL_HR_Admin"
                and password == "HBL@123"
            ):

                session["admin"] = True

                return redirect(
                    url_for("admin_dashboard")
                )

            flash(
                "Invalid Admin Username or Password",
                "danger"
            )

    return render_template("login.html")


# =========================================================
# EMPLOYEE DASHBOARD
# =========================================================

@app.route("/employee/dashboard")
def employee_dashboard():

    if "employee_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    employee = conn.execute("""
        SELECT *
        FROM employees
        WHERE employee_id = ?
    """, (
        session["employee_id"],
    )).fetchone()

    conn.close()

    return render_template(
        "employee_dashboard.html",
        employee=employee
    )


# =========================================================
# TOKEN PAGE
# =========================================================

@app.route("/employee/token/<token_type>")
def token_page(token_type):

    if "employee_id" not in session:
        return redirect(url_for("login"))

    valid_tokens = [
        "lunch",
        "tiffen",
        "tea"
    ]

    if token_type not in valid_tokens:
        return redirect(
            url_for("employee_dashboard")
        )

    conn = get_db()

    employee = conn.execute("""
        SELECT *
        FROM employees
        WHERE employee_id = ?
    """, (
        session["employee_id"],
    )).fetchone()

    conn.close()

    return render_template(
        "token.html",
        employee=employee,
        token_type=token_type
    )


# =========================================================
# ADD TOKEN
# =========================================================

@app.route(
    "/employee/add-token/<token_type>",
    methods=["POST"]
)
def add_token(token_type):

    if "employee_id" not in session:
        return redirect(url_for("login"))

    token_columns = {
        "lunch": "lunch_count",
        "tiffen": "tiffen_count",
        "tea": "tea_count"
    }

    if token_type not in token_columns:
        return redirect(
            url_for("employee_dashboard")
        )

    # Current date and time
    now = datetime.now()

    token_date = now.strftime("%Y-%m-%d")
    token_time = now.strftime("%I:%M:%S %p")

    employee_id = session["employee_id"]

    conn = get_db()

    # Update employee total count
    column = token_columns[token_type]

    conn.execute(f"""
        UPDATE employees
        SET {column} = {column} + 1
        WHERE employee_id = ?
    """, (
        employee_id,
    ))

    # Save individual token record
    conn.execute("""
        INSERT INTO token_records
        (
            employee_id,
            token_type,
            token_date,
            token_time
        )
        VALUES (?, ?, ?, ?)
    """, (
        employee_id,
        token_type,
        token_date,
        token_time
    ))

    conn.commit()
    conn.close()

    flash(
        f"{token_type.capitalize()} token added successfully!",
        "success"
    )

    return redirect(
        url_for(
            "token_page",
            token_type=token_type
        )
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get("admin"):
        return redirect(url_for("login"))

    return render_template(
        "admin_dashboard.html"
    )


# =========================================================
# EMPLOYEE MANAGEMENT
# =========================================================

@app.route("/admin/employee-management")
def employee_management():

    if not session.get("admin"):
        return redirect(url_for("login"))

    return render_template(
        "employee_management.html"
    )


# =========================================================
# ADD EMPLOYEE
# =========================================================

@app.route(
    "/admin/add-employee",
    methods=["GET", "POST"]
)
def add_employee():

    if not session.get("admin"):
        return redirect(url_for("login"))

    if request.method == "POST":

        employee_id = request.form.get(
            "employee_id"
        )

        employee_name = request.form.get(
            "employee_name"
        )

        department = request.form.get(
            "department"
        )

        conn = get_db()

        try:

            conn.execute("""
                INSERT INTO employees
                (
                    employee_id,
                    employee_name,
                    department
                )
                VALUES (?, ?, ?)
            """, (
                employee_id,
                employee_name,
                department
            ))

            conn.commit()

            flash(
                "Employee added successfully!",
                "success"
            )

            return redirect(
                url_for("employee_management")
            )

        except sqlite3.IntegrityError:

            flash(
                "Employee ID already exists!",
                "danger"
            )

        finally:

            conn.close()

    return render_template(
        "add_employee.html"
    )


# =========================================================
# UPDATE EMPLOYEE
# =========================================================

@app.route(
    "/admin/update-employee/<int:id>",
    methods=["GET", "POST"]
)
def update_employee(id):

    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = get_db()

    employee = conn.execute("""
        SELECT *
        FROM employees
        WHERE id = ?
    """, (
        id,
    )).fetchone()

    if not employee:

        conn.close()

        flash(
            "Employee not found!",
            "danger"
        )

        return redirect(
            url_for("search_employee")
        )

    if request.method == "POST":

        employee_id = request.form.get(
            "employee_id"
        )

        employee_name = request.form.get(
            "employee_name"
        )

        department = request.form.get(
            "department"
        )

        conn.execute("""
            UPDATE employees

            SET employee_id = ?,
                employee_name = ?,
                department = ?

            WHERE id = ?
        """, (
            employee_id,
            employee_name,
            department,
            id
        ))

        conn.commit()
        conn.close()

        flash(
            "Employee updated successfully!",
            "success"
        )

        return redirect(
            url_for("search_employee")
        )

    conn.close()

    return render_template(
        "update_employee.html",
        employee=employee
    )


# =========================================================
# DELETE EMPLOYEE
# =========================================================

@app.route("/admin/delete-employee/<int:id>")
def delete_employee(id):

    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = get_db()

    # Get employee ID first
    employee = conn.execute("""
        SELECT employee_id
        FROM employees
        WHERE id = ?
    """, (
        id,
    )).fetchone()

    if employee:

        # Delete token records
        conn.execute("""
            DELETE FROM token_records
            WHERE employee_id = ?
        """, (
            employee["employee_id"],
        ))

        # Delete employee
        conn.execute("""
            DELETE FROM employees
            WHERE id = ?
        """, (
            id,
        ))

        conn.commit()

        flash(
            "Employee deleted successfully!",
            "success"
        )

    conn.close()

    return redirect(
        url_for("search_employee")
    )


# =========================================================
# SEARCH EMPLOYEE
# =========================================================

@app.route(
    "/admin/search-employee",
    methods=["GET", "POST"]
)
def search_employee():

    if not session.get("admin"):
        return redirect(url_for("login"))

    employees = []

    if request.method == "POST":

        search = request.form.get(
            "search"
        )

        conn = get_db()

        employees = conn.execute("""
            SELECT *
            FROM employees

            WHERE employee_id LIKE ?
            OR employee_name LIKE ?
            OR department LIKE ?

            ORDER BY employee_name
        """, (
            "%" + search + "%",
            "%" + search + "%",
            "%" + search + "%"
        )).fetchall()

        conn.close()

    return render_template(
        "search_employee.html",
        employees=employees
    )


# =========================================================
# VIEW ALL EMPLOYEES
# =========================================================

@app.route("/admin/view")
def view():

    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = get_db()

    employees = conn.execute("""
        SELECT *
        FROM employees
        ORDER BY employee_name
    """).fetchall()

    conn.close()

    return render_template(
        "view.html",
        employees=employees
    )


# =========================================================
# EMPLOYEE DETAILS
# =========================================================

@app.route("/admin/employee-details/<int:id>")
def employee_details(id):

    if not session.get("admin"):
        return redirect(url_for("login"))

    conn = get_db()

    employee = conn.execute("""
        SELECT *
        FROM employees
        WHERE id = ?
    """, (
        id,
    )).fetchone()

    if not employee:

        conn.close()

        return redirect(
            url_for("view")
        )

    # Individual token history
    records = conn.execute("""
        SELECT *
        FROM token_records
        WHERE employee_id = ?
        ORDER BY id DESC
    """, (
        employee["employee_id"],
    )).fetchall()

    conn.close()

    total = (
        employee["lunch_count"]
        + employee["tiffen_count"]
        + employee["tea_count"]
    )

    return render_template(
        "employee_details.html",
        employee=employee,
        records=records,
        total=total
    )


# =========================================================
# TODAY REPORT
# =========================================================

@app.route("/admin/today")
def today_report():

    if not session.get("admin"):
        return redirect(url_for("login"))

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    display_date = datetime.now().strftime(
        "%d-%m-%Y"
    )

    conn = get_db()

    # Today's records
    records = conn.execute("""
        SELECT
            token_records.*,
            employees.employee_name,
            employees.department

        FROM token_records

        LEFT JOIN employees
        ON token_records.employee_id =
           employees.employee_id

        WHERE token_records.token_date = ?

        ORDER BY token_records.id DESC
    """, (
        today,
    )).fetchall()

    # Today's employee-wise summary
    summary = conn.execute("""
        SELECT

            employees.employee_id,
            employees.employee_name,
            employees.department,

            SUM(
                CASE
                    WHEN token_records.token_type = 'lunch'
                    THEN 1 ELSE 0
                END
            ) AS lunch_count,

            SUM(
                CASE
                    WHEN token_records.token_type = 'tiffen'
                    THEN 1 ELSE 0
                END
            ) AS tiffen_count,

            SUM(
                CASE
                    WHEN token_records.token_type = 'tea'
                    THEN 1 ELSE 0
                END
            ) AS tea_count

        FROM employees

        LEFT JOIN token_records
        ON employees.employee_id =
           token_records.employee_id

        AND token_records.token_date = ?

        GROUP BY
            employees.employee_id,
            employees.employee_name,
            employees.department

        ORDER BY employees.employee_name
    """, (
        today,
    )).fetchall()

    conn.close()

    return render_template(
        "today_report.html",
        records=records,
        summary=summary,
        display_date=display_date
    )


# =========================================================
# MONTHLY REPORT
# =========================================================

@app.route(
    "/admin/monthly",
    methods=["GET", "POST"]
)
def monthly_report():

    if not session.get("admin"):
        return redirect(url_for("login"))

    # Current month by default
    selected_month = request.form.get(
        "month"
    )

    if not selected_month:

        selected_month = datetime.now().strftime(
            "%Y-%m"
        )

    conn = get_db()

    # Monthly employee summary
    summary = conn.execute("""
        SELECT

            employees.employee_id,
            employees.employee_name,
            employees.department,

            SUM(
                CASE
                    WHEN token_records.token_type = 'lunch'
                    THEN 1 ELSE 0
                END
            ) AS lunch_count,

            SUM(
                CASE
                    WHEN token_records.token_type = 'tiffen'
                    THEN 1 ELSE 0
                END
            ) AS tiffen_count,

            SUM(
                CASE
                    WHEN token_records.token_type = 'tea'
                    THEN 1 ELSE 0
                END
            ) AS tea_count

        FROM employees

        LEFT JOIN token_records
        ON employees.employee_id =
           token_records.employee_id

        AND substr(
            token_records.token_date,
            1,
            7
        ) = ?

        GROUP BY
            employees.employee_id,
            employees.employee_name,
            employees.department

        ORDER BY employees.employee_name
    """, (
        selected_month,
    )).fetchall()

    # Detailed monthly records
    records = conn.execute("""
        SELECT

            token_records.*,
            employees.employee_name,
            employees.department

        FROM token_records

        LEFT JOIN employees
        ON token_records.employee_id =
           employees.employee_id

        WHERE substr(
            token_records.token_date,
            1,
            7
        ) = ?

        ORDER BY
            token_records.token_date DESC,
            token_records.id DESC
    """, (
        selected_month,
    )).fetchall()

    conn.close()

    # Display month
    try:

        display_month = datetime.strptime(
            selected_month,
            "%Y-%m"
        ).strftime("%B %Y")

    except ValueError:

        display_month = selected_month

    return render_template(
        "monthly_report.html",
        summary=summary,
        records=records,
        selected_month=selected_month,
        display_month=display_month
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )