import sqlite3
from datetime import datetime
import tkinter.messagebox as messagebox
from tkinter import ttk
import customtkinter as ctk

# ==================== إعدادات عامة ====================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
DB_NAME = "pos_database.db"


def get_db_connection():
    """إنشاء اتصال آمن بقاعدة البيانات"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# ==================== قاعدة البيانات ====================
def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute(
        """CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT UNIQUE,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        cost REAL DEFAULT 0,
        quantity INTEGER DEFAULT 0,
        category TEXT,
        supplier_id INTEGER)"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE,
        date TEXT,
        time TEXT,
        total REAL,
        discount REAL DEFAULT 0,
        status TEXT DEFAULT 'completed',
        shift TEXT,
        user TEXT)"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER,
        product_id INTEGER,
        barcode TEXT,
        name TEXT,
        quantity INTEGER,
        price REAL,
        total REAL)"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        notes TEXT)"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT)"""
    )

    # إضافة مستخدمين افتراضيين عند التشغيل لأول مرة
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("cashier", "123", "cashier"),
        )
        c.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            ("manager", "admin", "manager"),
        )

    # إضافة منتجات تجريبية
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        sample_products = [
            ("1001", "ماء معدني", 1.5, 0.8, 100, "مشروبات"),
            ("1002", "عصير برتقال", 3.0, 1.5, 80, "مشروبات"),
            ("1003", "شيبس", 2.5, 1.2, 50, "سناكس"),
            ("1004", "شوكولاتة", 4.0, 2.0, 60, "سناكس"),
            ("1005", "خبز", 1.0, 0.5, 200, "مخبوزات"),
        ]
        c.executemany(
            "INSERT INTO products (barcode, name, price, cost, quantity, category) VALUES (?, ?, ?, ?, ?, ?)",
            sample_products,
        )

    conn.commit()
    conn.close()


# ==================== نافذة تسجيل الدخول ====================
class LoginWindow(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title("نظام نقاط البيع - تسجيل الدخول")
        self.geometry("400x350")
        self.resizable(False, False)

        ctk.CTkLabel(
            self, text="تسجيل الدخول", font=("Arial", 24, "bold")
        ).pack(pady=20)

        self.username = ctk.CTkEntry(
            self, placeholder_text="اسم المستخدم", width=250
        )
        self.username.pack(pady=10)

        self.password = ctk.CTkEntry(
            self, placeholder_text="كلمة المرور", show="*", width=250
        )
        self.password.pack(pady=10)

        ctk.CTkButton(
            self, text="دخول", command=self.login, width=200, height=35
        ).pack(pady=20)

        ctk.CTkLabel(
            self,
            text="كاشير: cashier / 123\nمدير: manager / admin",
            font=("Arial", 12),
            text_color="gray",
        ).pack()

    def login(self):
        user = self.username.get().strip()
        pwd = self.password.get().strip()

        if not user or not pwd:
            messagebox.showwarning("تنبيه", "يرجى إدخال اسم المستخدم وكلمة المرور")
            return

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT role FROM users WHERE username=? AND password=?",
            (user, pwd),
        )
        result = c.fetchone()
        conn.close()

        if result:
            self.destroy()
            role = result["role"]
            if role == "cashier":
                CashierApp(user).mainloop()
            else:
                ManagerApp(user).mainloop()
        else:
            messagebox.showerror("خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة")


# ==================== واجهة الكاشير ====================
class CashierApp(ctk.CTk):

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.title(f"واجهة الكاشير - {username}")
        self.geometry("1200x750")
        self.state("zoomed")

        self.cart = []
        self.suspended_invoices = {}

        self.create_widgets()
        self.bind_shortcuts()

    def create_widgets(self):
        # الشريط العلوي
        top_frame = ctk.CTkFrame(self)
        top_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(top_frame, text="مسح الباركود:", font=("Arial", 16)).pack(
            side="left", padx=10
        )

        self.barcode_entry = ctk.CTkEntry(
            top_frame, width=220, font=("Arial", 16)
        )
        self.barcode_entry.pack(side="left", padx=5)
        self.barcode_entry.bind("<Return>", self.scan_product)
        self.barcode_entry.focus()

        ctk.CTkButton(
            top_frame,
            text="استعلام سعر (F5)",
            command=self.price_inquiry,
            width=130,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            top_frame,
            text="فاتورة جديدة (F1)",
            command=self.new_invoice,
            width=130,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            top_frame,
            text="تعليق فاتورة (F2)",
            command=self.suspend_invoice,
            width=130,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            top_frame,
            text="استرجاع معلقة (F3)",
            command=self.resume_invoice,
            width=130,
        ).pack(side="left", padx=5)

        # جدول سلة المشتريات
        self.tree_frame = ctk.CTkFrame(self)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("barcode", "name", "qty", "price", "total")
        self.tree = ttk.Treeview(
            self.tree_frame, columns=columns, show="headings", height=20
        )

        self.tree.heading("barcode", text="الباركود")
        self.tree.heading("name", text="اسم المنتج")
        self.tree.heading("qty", text="الكمية")
        self.tree.heading("price", text="السعر")
        self.tree.heading("total", text="الإجمالي")

        self.tree.column("barcode", width=120, anchor="center")
        self.tree.column("name", width=300, anchor="e")
        self.tree.column("qty", width=80, anchor="center")
        self.tree.column("price", width=100, anchor="center")
        self.tree.column("total", width=100, anchor="center")

        self.tree.pack(fill="both", expand=True, side="left")

        scrollbar = ttk.Scrollbar(
            self.tree_frame, orient="vertical", command=self.tree.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # الشريط السفلي
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.pack(fill="x", padx=10, pady=10)

        self.total_label = ctk.CTkLabel(
            bottom_frame, text="الإجمالي: 0.00", font=("Arial", 28, "bold")
        )
        self.total_label.pack(side="left", padx=20)

        ctk.CTkButton(
            bottom_frame,
            text="خروج (Esc)",
            command=self.quit_app,
            width=100,
            fg_color="gray",
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            bottom_frame,
            text="إنهاء الفاتورة",
            command=self.complete_invoice,
            fg_color="green",
            width=140,
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            bottom_frame,
            text="طباعة (F4)",
            command=self.print_invoice,
            width=120,
        ).pack(side="right", padx=5)
        ctk.CTkButton(
            bottom_frame,
            text="حذف منتج",
            command=self.remove_item,
            fg_color="red",
            width=110,
        ).pack(side="right", padx=5)

    def bind_shortcuts(self):
        self.bind("<F1>", lambda e: self.new_invoice())
        self.bind("<F2>", lambda e: self.suspend_invoice())
        self.bind("<F3>", lambda e: self.resume_invoice())
        self.bind("<F4>", lambda e: self.print_invoice())
        self.bind("<F5>", lambda e: self.price_inquiry())
        self.bind("<Escape>", lambda e: self.quit_app())

    def scan_product(self, event=None):
        barcode = self.barcode_entry.get().strip()
        if not barcode:
            return

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT id, name, price, quantity FROM products WHERE barcode=?",
            (barcode,),
        )
        product = c.fetchone()
        conn.close()

        if product:
            pid, name, price, stock = (
                product["id"],
                product["name"],
                product["price"],
                product["quantity"],
            )

            if stock <= 0:
                messagebox.showwarning("تنبيه", "المنتج غير متوفر في المخزون")
                self.barcode_entry.delete(0, "end")
                return

            # فحص إذا كان المنتج موجوداً مسبقاً بالسلة
            for item in self.cart:
                if item["barcode"] == barcode:
                    if item["qty"] + 1 > stock:
                        messagebox.showwarning(
                            "تنبيه", "الكمية المطلوبة تتجاوز المخزون المتوفر!"
                        )
                        self.barcode_entry.delete(0, "end")
                        return
                    item["qty"] += 1
                    item["total"] = item["qty"] * item["price"]
                    self.refresh_cart()
                    self.barcode_entry.delete(0, "end")
                    return

            # إضافة منتج جديد بالسلة
            self.cart.append(
                {
                    "product_id": pid,
                    "barcode": barcode,
                    "name": name,
                    "qty": 1,
                    "price": price,
                    "total": price,
                }
            )
            self.refresh_cart()
        else:
            messagebox.showerror("خطأ", "المنتج غير موجود")

        self.barcode_entry.delete(0, "end")

    def refresh_cart(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        total = 0.0
        for item in self.cart:
            self.tree.insert(
                "",
                "end",
                values=(
                    item["barcode"],
                    item["name"],
                    item["qty"],
                    f"{item['price']:.2f}",
                    f"{item['total']:.2f}",
                ),
            )
            total += item["total"]

        self.total_label.configure(text=f"الإجمالي: {total:.2f}")

    def remove_item(self):
        selected = self.tree.selection()
        if selected:
            index = self.tree.index(selected[0])
            del self.cart[index]
            self.refresh_cart()
        else:
            messagebox.showinfo("تنبيه", "حدد منتجاً لحذفه من السلة")

    def new_invoice(self):
        if self.cart:
            if not messagebox.askyesno(
                "تأكيد", "هل تريد إلغاء الفاتورة الحالية؟"
            ):
                return
        self.cart = []
        self.refresh_cart()
        self.barcode_entry.focus()

    def suspend_invoice(self):
        if not self.cart:
            messagebox.showinfo("تنبيه", "لا توجد منتجات لتعليقها")
            return

        key = f"فاتورة_{datetime.now().strftime('%H:%M:%S')}"
        self.suspended_invoices[key] = self.cart.copy()
        self.cart = []
        self.refresh_cart()
        messagebox.showinfo("تم", f"تم تعليق الفاتورة بنجاح باسم: {key}")

    def resume_invoice(self):
        if not self.suspended_invoices:
            messagebox.showinfo("تنبيه", "لا توجد فواتير معلقة")
            return

        win = ctk.CTkToplevel(self)
        win.title("الفواتير المعلقة")
        win.geometry("350x200")
        win.grab_set()

        ctk.CTkLabel(win, text="اختر الفاتورة المعلقة:").pack(pady=10)

        options = list(self.suspended_invoices.keys())
        selected_option = ctk.StringVar(value=options[0])

        option_menu = ctk.CTkOptionMenu(
            win, variable=selected_option, values=options
        )
        option_menu.pack(pady=10)

        def load():
            key = selected_option.get()
            if key in self.suspended_invoices:
                self.cart = self.suspended_invoices.pop(key)
                self.refresh_cart()
                win.destroy()

        ctk.CTkButton(win, text="استرجاع الفاتورة", command=load).pack(pady=15)

    def complete_invoice(self):
        if not self.cart:
            messagebox.showinfo("تنبيه", "الفاتورة فارغة")
            return

        total = sum(item["total"] for item in self.cart)
        now = datetime.now()
        invoice_number = now.strftime("%Y%m%d%H%M%S")

        conn = get_db_connection()
        c = conn.cursor()

        try:
            c.execute(
                """INSERT INTO invoices (invoice_number, date, time, total, status, shift, user) 
                         VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    invoice_number,
                    now.strftime("%Y-%m-%d"),
                    now.strftime("%H:%M:%S"),
                    total,
                    "completed",
                    "صباحية",
                    self.username,
                ),
            )

            invoice_id = c.lastrowid

            for item in self.cart:
                c.execute(
                    """INSERT INTO invoice_items (invoice_id, product_id, barcode, name, quantity, price, total) 
                             VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        invoice_id,
                        item["product_id"],
                        item["barcode"],
                        item["name"],
                        item["qty"],
                        item["price"],
                        item["total"],
                    ),
                )

                c.execute(
                    "UPDATE products SET quantity = quantity - ? WHERE id = ?",
                    (item["qty"], item["product_id"]),
                )

            conn.commit()
            messagebox.showinfo(
                "نجاح",
                f"تم حفظ الفاتورة بنجاح!\nرقم الفاتورة: {invoice_number}\nالإجمالي: {total:.2f}",
            )
            self.cart = []
            self.refresh_cart()
        except Exception as e:
            conn.rollback()
            messagebox.showerror(
                "خطأ في قاعدة البيانات", f"حدث خطأ أثناء حفظ الفاتورة: {e}"
            )
        finally:
            conn.close()

    def print_invoice(self):
        if not self.cart:
            messagebox.showinfo("تنبيه", "لا توجد فاتورة للطباعة")
            return
        messagebox.showinfo(
            "طباعة", "تم إرسال الفاتورة للطابعة (وظيفة محاكاة للطباعة)"
        )

    def price_inquiry(self):
        barcode = self.barcode_entry.get().strip()
        if not barcode:
            messagebox.showinfo("استعلام", "أدخل الباركود في الحقل أولاً")
            return

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT name, price, quantity FROM products WHERE barcode=?",
            (barcode,),
        )
        product = c.fetchone()
        conn.close()

        if product:
            messagebox.showinfo(
                "استعلام عن منتج",
                f"اسم المنتج: {product['name']}\nالسعر: {product['price']:.2f}\nالكمية المتبقية: {product['quantity']}",
            )
        else:
            messagebox.showerror("خطأ", "المنتج غير موجود")

        self.barcode_entry.delete(0, "end")

    def quit_app(self):
        if messagebox.askyesno("خروج", "هل تريد الخروج من برنامج الكاشير؟"):
            self.destroy()


# ==================== واجهة المدير ====================
class ManagerApp(ctk.CTk):

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.title(f"لوحة تحكم المدير - {username}")
        self.geometry("1300x800")
        self.state("zoomed")

        self.create_widgets()

    def create_widgets(self):
        sidebar = ctk.CTkFrame(self, width=200)
        sidebar.pack(side="left", fill="y", padx=5, pady=5)

        ctk.CTkLabel(
            sidebar, text="لوحة التحكم", font=("Arial", 20, "bold")
        ).pack(pady=20)

        buttons = [
            ("المنتجات", self.show_products),
            ("سجل الفواتير", self.show_invoices),
            ("حالة المخزون", self.show_stock),
            ("الموردين", self.show_suppliers),
            ("المبيعات اليومية", self.show_daily_sales),
            ("خروج", self.quit_app),
        ]

        for text, cmd in buttons:
            ctk.CTkButton(
                sidebar, text=text, command=cmd, width=180, height=40
            ).pack(pady=8)

        self.content = ctk.CTkFrame(self)
        self.content.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        self.show_products()

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def show_products(self):
        self.clear_content()
        ctk.CTkLabel(
            self.content, text="إدارة المنتجات", font=("Arial", 22, "bold")
        ).pack(pady=10)

        form = ctk.CTkFrame(self.content)
        form.pack(fill="x", padx=20, pady=10)

        self.p_barcode = ctk.CTkEntry(form, placeholder_text="الباركود")
        self.p_barcode.grid(row=0, column=0, padx=5, pady=5)

        self.p_name = ctk.CTkEntry(
            form, placeholder_text="اسم المنتج", width=180
        )
        self.p_name.grid(row=0, column=1, padx=5, pady=5)

        self.p_price = ctk.CTkEntry(form, placeholder_text="السعر")
        self.p_price.grid(row=0, column=2, padx=5, pady=5)

        self.p_qty = ctk.CTkEntry(form, placeholder_text="الكمية")
        self.p_qty.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkButton(
            form, text="إضافة منتج", command=self.add_product, fg_color="green"
        ).grid(row=0, column=4, padx=10)

        columns = ("id", "barcode", "name", "price", "qty")
        self.product_tree = ttk.Treeview(
            self.content, columns=columns, show="headings"
        )

        self.product_tree.heading("id", text="المعرف")
        self.product_tree.heading("barcode", text="الباركود")
        self.product_tree.heading("name", text="اسم المنتج")
        self.product_tree.heading("price", text="السعر")
        self.product_tree.heading("qty", text="الكمية")

        for col in columns:
            self.product_tree.column(col, anchor="center")

        self.product_tree.pack(fill="both", expand=True, padx=20, pady=10)
        self.load_products()

    def load_products(self):
        for i in self.product_tree.get_children():
            self.product_tree.delete(i)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT id, barcode, name, price, quantity FROM products")
        for row in c.fetchall():
            self.product_tree.insert("", "end", values=tuple(row))
        conn.close()

    def add_product(self):
        barcode = self.p_barcode.get().strip()
        name = self.p_name.get().strip()
        price = self.p_price.get().strip()
        qty = self.p_qty.get().strip()

        if not barcode or not name or not price or not qty:
            messagebox.showwarning("تنبيه", "جميع الحقول مطلوبة!")
            return

        try:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                "INSERT INTO products (barcode, name, price, quantity) VALUES (?, ?, ?, ?)",
                (barcode, name, float(price), int(qty)),
            )
            conn.commit()
            conn.close()

            messagebox.showinfo("نجاح", "تمت إضافة المنتج بنجاح")

            self.p_barcode.delete(0, "end")
            self.p_name.delete(0, "end")
            self.p_price.delete(0, "end")
            self.p_qty.delete(0, "end")

            self.load_products()
        except sqlite3.IntegrityError:
            messagebox.showerror("خطأ", "رمز الباركود موجود مسبقاً!")
        except ValueError:
            messagebox.showerror("خطأ", "تأكد من إدخال قيم صالحة للسعر والكمية")

    def show_invoices(self):
        self.clear_content()
        ctk.CTkLabel(
            self.content, text="سجل الفواتير", font=("Arial", 22, "bold")
        ).pack(pady=10)

        columns = ("id", "number", "date", "time", "total", "user")
        tree = ttk.Treeview(self.content, columns=columns, show="headings")

        tree.heading("id", text="#")
        tree.heading("number", text="رقم الفاتورة")
        tree.heading("date", text="التاريخ")
        tree.heading("time", text="الوقت")
        tree.heading("total", text="الإجمالي")
        tree.heading("user", text="المستخدم")

        for col in columns:
            tree.column(col, anchor="center")

        tree.pack(fill="both", expand=True, padx=20, pady=10)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT id, invoice_number, date, time, total, user FROM invoices ORDER BY id DESC"
        )
        for row in c.fetchall():
            tree.insert("", "end", values=tuple(row))
        conn.close()

    def show_stock(self):
        self.clear_content()
        ctk.CTkLabel(
            self.content,
            text="تقرير المخزون الحالي",
            font=("Arial", 22, "bold"),
        ).pack(pady=10)

        columns = ("barcode", "name", "qty", "price")
        tree = ttk.Treeview(self.content, columns=columns, show="headings")

        tree.heading("barcode", text="الباركود")
        tree.heading("name", text="اسم المنتج")
        tree.heading("qty", text="الكمية المتبقية")
        tree.heading("price", text="سعر البيع")

        for col in columns:
            tree.column(col, anchor="center")

        tree.pack(fill="both", expand=True, padx=20, pady=10)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT barcode, name, quantity, price FROM products ORDER BY quantity ASC"
        )
        for row in c.fetchall():
            tree.insert("", "end", values=tuple(row))
        conn.close()

    def show_suppliers(self):
        self.clear_content()
        ctk.CTkLabel(
            self.content, text="قائمة الموردين", font=("Arial", 22, "bold")
        ).pack(pady=10)
        ctk.CTkLabel(
            self.content,
            text="سيتم إضافة هذه الميزة في التحديث القادم.",
            font=("Arial", 16),
            text_color="gray",
        ).pack(pady=50)

    def show_daily_sales(self):
        self.clear_content()
        ctk.CTkLabel(
            self.content, text="التحصيل اليومي", font=("Arial", 22, "bold")
        ).pack(pady=10)

        today = datetime.now().strftime("%Y-%m-%d")

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "SELECT COUNT(*), SUM(total) FROM invoices WHERE date=? AND status='completed'",
            (today,),
        )
        row = c.fetchone()
        conn.close()

        count = row[0] if row else 0
        total = row[1] if row and row[1] is not None else 0.0

        card = ctk.CTkFrame(self.content)
        card.pack(pady=30, padx=30, fill="x")

        ctk.CTkLabel(
            card, text=f"تاريخ اليوم: {today}", font=("Arial", 18)
        ).pack(pady=10)
        ctk.CTkLabel(
            card, text=f"عدد الفواتير المُصدرة: {count}", font=("Arial", 18)
        ).pack(pady=5)
        ctk.CTkLabel(
            card,
            text=f"إجمالي مبيعات اليوم: {total:.2f} $",
            font=("Arial", 26, "bold"),
            text_color="#2FA572",
        ).pack(pady=15)

    def quit_app(self):
        self.destroy()


# ==================== تشغيل البرنامج ====================
if __name__ == "__main__":
    init_db()
    app = LoginWindow()
    app.mainloop()
