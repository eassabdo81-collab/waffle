from flask import Flask, request, redirect, url_for, session, flash, render_template_string
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB = "graveyard.db"

# ================= DATABASE =================
def connect_db():
    return sqlite3.connect(DB)

def setup_db():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        years_paid INTEGER,
        years_due INTEGER,
        year_cost REAL,
        start_year INTEGER
    )
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("""
        INSERT INTO users (name, username, password, role, years_paid, years_due, year_cost, start_year)
        VALUES (?, ?, ?, 'admin', 0, 0, 0, 2026)
        """, ("مدير النظام", "admin", hash_password("Admin@123")))
        conn.commit()
    conn.close()

setup_db()
create_admin()

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = hash_password(request.form["password"])
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT user_id, role FROM users WHERE username=? AND password=?", (username, password))
        res = cur.fetchone()
        conn.close()
        if res:
            session["user_id"] = res[0]
            session["role"] = res[1]
            if res[1] == "admin":
                return redirect(url_for("admin_panel"))
            else:
                return redirect(url_for("user_panel"))
        else:
            flash("اسم المستخدم أو كلمة المرور غير صحيحة", "danger")
    return render_template_string("""
<!doctype html>
<html>
<head><title>تسجيل الدخول</title></head>
<body>
<h2>تسجيل الدخول</h2>
{% with messages = get_flashed_messages(with_categories=true) %}
  {% for category, msg in messages %}
    <p style="color:red">{{ msg }}</p>
  {% endfor %}
{% endwith %}
<form method="POST">
    اسم المستخدم: <input type="text" name="username"><br>
    كلمة المرور: <input type="password" name="password"><br>
    <input type="submit" value="دخول">
</form>
</body>
</html>
""")

# ================= ADMIN PANEL =================
@app.route("/admin")
def admin_panel():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE role='user'")
    users = cur.fetchall()
    conn.close()
    return render_template_string("""
<!doctype html>
<html>
<head><title>لوحة المدير</title></head>
<body>
<h2>لوحة المدير</h2>
<a href="{{ url_for('logout') }}">تسجيل الخروج</a>
<h3>إضافة مستخدم</h3>
<form method="POST" action="{{ url_for('add_user') }}">
    الاسم: <input type="text" name="name">
    اسم المستخدم: <input type="text" name="username">
    كلمة المرور: <input type="password" name="password">
    سنوات مستحقة: <input type="number" name="years_due">
    قيمة السنة: <input type="number" step="0.01" name="year_cost">
    سنة الاشتراك: <input type="number" name="start_year">
    <input type="submit" value="إضافة">
</form>

<h3>المستخدمين</h3>
<table border="1">
<tr>
<th>ID</th><th>الاسم</th><th>سنوات مدفوعة</th><th>سنوات مستحقة</th><th>قيمة السنة</th><th>المبلغ المستحق</th><th>سنة الاشتراك</th><th>إجراءات</th>
</tr>
{% for u in users %}
<tr>
<td>{{ u[0] }}</td>
<td>{{ u[1] }}</td>
<td>{{ u[5] }}</td>
<td>{{ u[6] }}</td>
<td>{{ u[7] }}</td>
<td>{{ u[6]*u[7] }}</td>
<td>{{ u[8] }}</td>
<td>
<form method="POST" action="{{ url_for('pay_years', user_id=u[0]) }}" style="display:inline">
<input type="number" name="years" min="1">
<input type="submit" value="دفع سنة">
</form>
<form method="POST" action="{{ url_for('edit_user', user_id=u[0]) }}" style="display:inline">
<input type="submit" value="تعديل">
</form>
<a href="{{ url_for('delete_user', user_id=u[0]) }}" onclick="return confirm('هل تريد حذف المستخدم؟')">حذف</a>
</td>
</tr>
{% endfor %}
</table>

{% with messages = get_flashed_messages(with_categories=true) %}
  {% for category, msg in messages %}
    <p style="color:green">{{ msg }}</p>
  {% endfor %}
{% endwith %}
</body>
</html>
""", users=users)

# ================= ADD USER =================
@app.route("/add_user", methods=["POST"])
def add_user():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    name = request.form["name"]
    username = request.form["username"]
    password = request.form["password"]
    years_due = int(request.form["years_due"])
    year_cost = float(request.form["year_cost"])
    start_year = int(request.form["start_year"])
    conn = connect_db()
    cur = conn.cursor()
    try:
        cur.execute("""
        INSERT INTO users (name, username, password, role, years_paid, years_due, year_cost, start_year)
        VALUES (?, ?, ?, 'user', 0, ?, ?, ?)
        """, (name, username, hash_password(password), years_due, year_cost, start_year))
        conn.commit()
        flash("تم إضافة المستخدم", "success")
    except sqlite3.IntegrityError:
        flash("اسم المستخدم موجود بالفعل", "danger")
    finally:
        conn.close()
    return redirect(url_for("admin_panel"))

# ================= EDIT USER =================
@app.route("/edit_user/<int:user_id>", methods=["POST", "GET"])
def edit_user(user_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    conn = connect_db()
    cur = conn.cursor()
    if request.method=="POST":
        name = request.form["name"]
        years_paid = int(request.form["years_paid"])
        years_due = int(request.form["years_due"])
        year_cost = float(request.form["year_cost"])
        start_year = int(request.form["start_year"])
        cur.execute("""
            UPDATE users SET name=?, years_paid=?, years_due=?, year_cost=?, start_year=?
            WHERE user_id=?
        """, (name, years_paid, years_due, year_cost, start_year, user_id))
        conn.commit()
        conn.close()
        flash("تم تعديل بيانات المستخدم", "success")
        return redirect(url_for("admin_panel"))
    else:
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        user = cur.fetchone()
        conn.close()
        return render_template_string("""
<form method="POST">
الاسم: <input type="text" name="name" value="{{ user[1] }}"><br>
سنوات مدفوعة: <input type="number" name="years_paid" value="{{ user[5] }}"><br>
سنوات مستحقة: <input type="number" name="years_due" value="{{ user[6] }}"><br>
قيمة السنة: <input type="number" step="0.01" name="year_cost" value="{{ user[7] }}"><br>
سنة الاشتراك: <input type="number" name="start_year" value="{{ user[8] }}"><br>
<input type="submit" value="حفظ">
</form>
""", user=user)

# ================= DELETE USER =================
@app.route("/delete_user/<int:user_id>")
def delete_user(user_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("تم حذف المستخدم", "success")
    return redirect(url_for("admin_panel"))

# ================= PAY YEARS =================
@app.route("/pay/<int:user_id>", methods=["POST"])
def pay_years(user_id):
    if "role" not in session:
        return redirect(url_for("login"))
    years = int(request.form["years"])
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT years_paid, years_due, year_cost FROM users WHERE user_id=?", (user_id,))
    paid, due, cost = cur.fetchone()
    if years > due:
        years = due
    paid += years
    due -= years
    cur.execute("UPDATE users SET years_paid=?, years_due=? WHERE user_id=?", (paid, due, user_id))
    conn.commit()
    conn.close()
    flash(f"تم دفع {years} سنة بقيمة {years*cost} جنيه", "success")
    if session["role"] == "admin":
        return redirect(url_for("admin_panel"))
    else:
        return redirect(url_for("user_panel"))

# ================= USER PANEL =================
@app.route("/user")
def user_panel():
    if "user_id" not in session or session["role"] != "user":
        return redirect(url_for("login"))
    user_id = session["user_id"]
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return render_template_string("""
<h2>حسابك</h2>
<a href="{{ url_for('logout') }}">تسجيل الخروج</a>
<p>الاسم: {{ user[1] }}</p>
<p>سنوات مدفوعة: {{ user[5] }}</p>
<p>سنوات مستحقة: {{ user[6] }}</p>
<p>المبلغ المستحق: {{ user[6]*user[7] }} جنيه</p>
<p>سنة الاشتراك: {{ user[8] }}</p>

<form method="POST" action="{{ url_for('pay_years', user_id=user[0]) }}">
    دفع سنوات: <input type="number" name="years" min="1">
    <input type="submit" value="دفع">
</form>
""", user=user)

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
