import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import hashlib

# ================= DATABASE =================
def connect_db():
    return sqlite3.connect("graveyard.db")

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

# ================= LOGIN =================
def login():
    username = entry_user.get()
    password = hash_password(entry_pass.get())
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT user_id, role FROM users WHERE username=? AND password=?", (username, password))
    res = cur.fetchone()
    conn.close()
    if res:
        root.destroy()
        user_id, role = res
        if role == "admin":
            admin_panel()
        else:
            user_panel(user_id)
    else:
        messagebox.showerror("خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة")

# ================= ADMIN PANEL =================
def admin_panel():
    win = tk.Tk()
    win.title("لوحة تحكم المدير")
    win.geometry("950x450")

    tk.Label(win, text="لوحة التحكم - جميع المستخدمين", font=("Arial", 14)).pack(pady=10)

    columns = ("ID", "الاسم", "سنوات مدفوعة", "سنوات مستحقة", "سعر السنة", "المبلغ المستحق", "سنة الاشتراك")
    tree = ttk.Treeview(win, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=130)
    tree.pack(fill="both", expand=True)

    # ======== LOAD USERS ========
    def load_users():
        for row in tree.get_children():
            tree.delete(row)
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT user_id, name, years_paid, years_due, year_cost, start_year FROM users WHERE role='user'")
        for u in cur.fetchall():
            amount_due = u[3] * u[4]
            tree.insert("", "end", values=(u[0], u[1], u[2], u[3], u[4], amount_due, u[5]))
        conn.close()

    load_users()

    # ======== ADD USER ========
    def add_user():
        name = simpledialog.askstring("إضافة مستخدم", "ادخل الاسم:")
        if not name: return
        username = simpledialog.askstring("إضافة مستخدم", "ادخل اسم المستخدم:")
        if not username: return
        password = simpledialog.askstring("إضافة مستخدم", "ادخل كلمة المرور:", show="*")
        if not password: return
        years_due = simpledialog.askinteger("إضافة مستخدم", "كم عدد السنوات المستحقة؟", minvalue=1)
        year_cost = simpledialog.askfloat("إضافة مستخدم", "كم قيمة السنة الواحدة؟", minvalue=0)
        start_year = simpledialog.askinteger("إضافة مستخدم", "ادخل السنة التي بدأ فيها الاشتراك:", minvalue=2000, maxvalue=2100)
        conn = connect_db()
        cur = conn.cursor()
        try:
            cur.execute("""
            INSERT INTO users (name, username, password, role, years_paid, years_due, year_cost, start_year)
            VALUES (?, ?, ?, 'user', 0, ?, ?, ?)
            """, (name, username, hash_password(password), years_due, year_cost, start_year))
            conn.commit()
            messagebox.showinfo("تم", "تم إضافة المستخدم")
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "اسم المستخدم موجود بالفعل")
        finally:
            conn.close()
        load_users()

    # ======== PAY YEAR ========
    def pay_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر مستخدم أولاً")
            return
        user_id = tree.item(selected[0])["values"][0]
        years = simpledialog.askinteger("دفع", "كم عدد السنوات التي تريد دفعها؟", minvalue=1)
        if years is None: return
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT years_paid, years_due, year_cost FROM users WHERE user_id=?", (user_id,))
        paid, due, cost = cur.fetchone()
        if years > due:
            messagebox.showwarning("تحذير", f"عدد السنوات أكبر من المستحقة ({due})")
            years = due
        paid += years
        due -= years
        cur.execute("UPDATE users SET years_paid=?, years_due=? WHERE user_id=?", (paid, due, user_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("تم", f"تم دفع {years} سنة بقيمة {years*cost} جنيه")
        load_users()

    # ======== DELETE USER ========
    def delete_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر مستخدم أولاً")
            return
        user_id = tree.item(selected[0])["values"][0]
        if messagebox.askyesno("تأكيد", "هل تريد حذف هذا المستخدم؟"):
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE user_id=?", (user_id,))
            conn.commit()
            conn.close()
            load_users()
            messagebox.showinfo("تم", "تم حذف المستخدم")

    # ======== EDIT USER ========
    def edit_selected():
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("تحذير", "اختر مستخدم أولاً")
            return
        user_id = tree.item(selected[0])["values"][0]

        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT name, years_paid, years_due, year_cost, start_year FROM users WHERE user_id=?", (user_id,))
        user = cur.fetchone()
        conn.close()

        edit_win = tk.Toplevel()
        edit_win.title("تعديل المستخدم")

        tk.Label(edit_win, text="الاسم").grid(row=0, column=0, padx=5, pady=5)
        name_e = tk.Entry(edit_win)
        name_e.grid(row=0, column=1, padx=5, pady=5)
        name_e.insert(0, user[0])

        tk.Label(edit_win, text="سنوات مدفوعة").grid(row=1, column=0, padx=5, pady=5)
        paid_e = tk.Entry(edit_win)
        paid_e.grid(row=1, column=1, padx=5, pady=5)
        paid_e.insert(0, user[1])

        tk.Label(edit_win, text="سنوات مستحقة").grid(row=2, column=0, padx=5, pady=5)
        due_e = tk.Entry(edit_win)
        due_e.grid(row=2, column=1, padx=5, pady=5)
        due_e.insert(0, user[2])

        tk.Label(edit_win, text="قيمة السنة").grid(row=3, column=0, padx=5, pady=5)
        cost_e = tk.Entry(edit_win)
        cost_e.grid(row=3, column=1, padx=5, pady=5)
        cost_e.insert(0, user[3])

        tk.Label(edit_win, text="سنة الاشتراك").grid(row=4, column=0, padx=5, pady=5)
        start_e = tk.Entry(edit_win)
        start_e.grid(row=4, column=1, padx=5, pady=5)
        start_e.insert(0, user[4])

        def save_changes():
            try:
                new_name = name_e.get()
                new_paid = int(paid_e.get())
                new_due = int(due_e.get())
                new_cost = float(cost_e.get())
                new_start = int(start_e.get())
                conn = connect_db()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE users 
                    SET name=?, years_paid=?, years_due=?, year_cost=?, start_year=? 
                    WHERE user_id=?
                """, (new_name, new_paid, new_due, new_cost, new_start, user_id))
                conn.commit()
                conn.close()
                messagebox.showinfo("تم", "تم تعديل بيانات المستخدم")
                edit_win.destroy()
                load_users()
            except ValueError:
                messagebox.showerror("خطأ", "تأكد من صحة البيانات المدخلة")

        tk.Button(edit_win, text="حفظ التعديلات", command=save_changes).grid(row=5, column=0, columnspan=2, pady=10)

    # ======== BUTTONS ========
    btn_frame = tk.Frame(win)
    btn_frame.pack(pady=10)
    tk.Button(btn_frame, text="➕ إضافة مستخدم", command=add_user).pack(side="left", padx=5)
    tk.Button(btn_frame, text="💰 دفع سنة للمستخدم المحدد", command=pay_selected).pack(side="left", padx=5)
    tk.Button(btn_frame, text="🗑️ حذف المستخدم المحدد", command=delete_selected).pack(side="left", padx=5)
    tk.Button(btn_frame, text="✏️ تعديل المستخدم المحدد", command=edit_selected).pack(side="left", padx=5)
    tk.Button(btn_frame, text="🔄 تحديث الجدول", command=load_users).pack(side="left", padx=5)

    win.mainloop()

# ================= USER PANEL =================
def user_panel(user_id):
    win = tk.Tk()
    win.title("حساب المستخدم")
    win.geometry("350x300")

    def refresh():
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT name, years_paid, years_due, year_cost, start_year FROM users WHERE user_id=?", (user_id,))
        u = cur.fetchone()
        conn.close()
        for widget in win.winfo_children():
            widget.destroy()
        amount_due = u[2] * u[3]
        tk.Label(win, text=f"الاسم: {u[0]}").pack(pady=5)
        tk.Label(win, text=f"سنوات مدفوعة: {u[1]}").pack(pady=5)
        tk.Label(win, text=f"سنوات مستحقة: {u[2]}").pack(pady=5)
        tk.Label(win, text=f"المبلغ المستحق: {amount_due} جنيه").pack(pady=5)
        tk.Label(win, text=f"سنة الاشتراك: {u[4]}").pack(pady=5)

        def pay_years_user():
            years = simpledialog.askinteger("دفع", "كم عدد السنوات التي تريد دفعها؟", minvalue=1)
            if years is None: return
            conn = connect_db()
            cur = conn.cursor()
            cur.execute("SELECT years_paid, years_due, year_cost FROM users WHERE user_id=?", (user_id,))
            paid, due, cost = cur.fetchone()
            if years > due:
                messagebox.showwarning("تحذير", f"عدد السنوات أكبر من المستحقة ({due})")
                years = due
            paid += years
            due -= years
            cur.execute("UPDATE users SET years_paid=?, years_due=? WHERE user_id=?", (paid, due, user_id))
            conn.commit()
            conn.close()
            messagebox.showinfo("تم", f"تم دفع {years} سنة بقيمة {years*cost} جنيه")
            refresh()

        tk.Button(win, text="💰 دفع سنة", command=pay_years_user).pack(pady=5)

    refresh()
    win.mainloop()

# ================= START =================
setup_db()
create_admin()

root = tk.Tk()
root.title("تسجيل الدخول")
root.geometry("300x220")

tk.Label(root, text="اسم المستخدم").pack()
entry_user = tk.Entry(root)
entry_user.pack()

tk.Label(root, text="كلمة المرور").pack()
entry_pass = tk.Entry(root, show="*")
entry_pass.pack()

tk.Button(root, text="دخول", command=login).pack(pady=10)

root.mainloop()
