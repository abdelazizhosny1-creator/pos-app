import os
import sqlite3
import sys
from datetime import datetime
from tkinter import messagebox
import customtkinter as ctk

# إعداد مظهر التطبيق
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DB_NAME = "pos_database.db"


def resource_path(relative_path):
  """إحضار المسار المطلق للملفات سواء عند التشغيل العادي أو من ملف EXE"""
  try:
    base_path = sys._MEIPASS
  except Exception:
    base_path = os.path.abspath(".")
  return os.path.join(base_path, relative_path)


def get_db_connection():
  conn = sqlite3.connect(DB_NAME)
  conn.row_factory = sqlite3.Row
  return conn


def init_db():
  conn = get_db_connection()
  c = conn.cursor()

  # جدول المنتجات
  c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            cost REAL DEFAULT 0,
            quantity INTEGER DEFAULT 0,
            category TEXT,
            supplier_id INTEGER
        )
    """)

  # جدول الفواتير
  c.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT UNIQUE,
            date TEXT,
            total REAL,
            discount REAL DEFAULT 0,
            status TEXT DEFAULT 'completed',
            shift_id INTEGER,
            user TEXT
        )
    """)

  # تفاصيل الفواتير
  c.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER,
            product_id INTEGER,
            barcode TEXT,
            name TEXT,
            quantity INTEGER,
            price REAL,
            total REAL
        )
    """)

  # الفواتير المعلقة
  c.execute("""
        CREATE TABLE IF NOT EXISTS held_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hold_time TEXT,
            data TEXT
        )
    """)

  # جدول الموردين
  c.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            notes TEXT
        )
    """)

  # جدول المستخدمين
  c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

  # إضافة مستخدم افتراضي إذا لم يوجد
  c.execute("SELECT COUNT(*) FROM users")
  if c.fetchone()[0] == 0:
    c.execute(
        "INSERT INTO users (username, password, role) VALUES ('admin',"
        " 'admin', 'admin')"
    )
    c.execute(
        "INSERT INTO users (username, password, role) VALUES ('cashier',"
        " '1234', 'cashier')"
    )

  conn.commit()
  conn.close()


class POSApp(ctk.CTk):

  def __init__(self):
    super().__init__()
    self.title("نظام إدارة المبيعات والمخزون - POS")
    self.geometry("1100x700")

    self.current_user = None
    self.cart = []  # سلة المشتريات الحالية
    self.held_invoices = []  # الفواتير المعلقة

    self.show_login()

  def clear_screen(self):
    for widget in self.winfo_children():
      widget.destroy()

  # -------------------------------------------------------------
  # شاشة تسجيل الدخول
  # -------------------------------------------------------------
  def show_login(self):
    self.clear_screen()
    frame = ctk.CTkFrame(self, width=350, height=400)
    frame.place(relx=0.5, rely=0.5, anchor="center")

    ctk.CTkLabel(
        frame, text="تسجيل الدخول", font=ctk.CTkFont(size=22, weight="bold")
    ).pack(pady=20)

    self.user_entry = ctk.CTkEntry(
        frame, placeholder_text="اسم المستخدم", width=250
    )
    self.user_entry.pack(pady=10)

    self.pass_entry = ctk.CTkEntry(
        frame, placeholder_text="كلمة المرور", show="*", width=250
    )
    self.pass_entry.pack(pady=10)

    ctk.CTkButton(
        frame, text="دخول", width=250, command=self.check_login
    ).pack(pady=20)

  def check_login(self):
    username = self.user_entry.get()
    password = self.pass_entry.get()

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password),
    )
    user = c.fetchone()
    conn.close()

    if user:
      self.current_user = dict(user)
      if self.current_user["role"] == "admin":
        self.show_admin_dashboard()
      else:
        self.show_cashier_interface()
    else:
      messagebox.showerror(
          "خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة!"
      )

  # -------------------------------------------------------------
  # واجهة الكاشير
  # -------------------------------------------------------------
  def show_cashier_interface(self):
    self.clear_screen()

    # شريط الاختصارات العلوي
    top_bar = ctk.CTkFrame(self, height=40)
    top_bar.pack(fill="x", padx=10, pady=5)

    shortcuts_text = (
        "F1: فاتورة جديدة | F2: تعليق الفاتورة | F3: الفواتير المعلقة | F4:"
        " استعلام عن سعر | F5: طباعة وإتمام | Esc: خروج"
    )
    ctk.CTkLabel(
        top_bar, text=shortcuts_text, font=ctk.CTkFont(size=12, weight="bold")
    ).pack(side="left", padx=10)

    # قسم الإدخال والبحث
    input_frame = ctk.CTkFrame(self)
    input_frame.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(input_frame, text="الباركود / اسم المنتج:").pack(
        side="right", padx=5
    )
    self.barcode_entry = ctk.CTkEntry(input_frame, width=300)
    self.barcode_entry.pack(side="right", padx=5)
    self.barcode_entry.bind("<Return>", self.add_to_cart)
    self.barcode_entry.focus()

    # جدول السلة (قائمة المنتجات)
    self.cart_frame = ctk.CTkScrollableFrame(self, height=350)
    self.cart_frame.pack(fill="both", expand=True, padx=10, pady=5)

    # شريط الإجمالي والأزرار
    bottom_frame = ctk.CTkFrame(self)
    bottom_frame.pack(fill="x", padx=10, pady=10)

    self.total_label = ctk.CTkLabel(
        bottom_frame,
        text="الإجمالي: 0.00 ج.م",
        font=ctk.CTkFont(size=24, weight="bold"),
        text_color="green",
    )
    self.total_label.pack(side="right", padx=20)

    ctk.CTkButton(
        bottom_frame,
        text="إتمام وطباعة (F5)",
        fg_color="green",
        command=self.checkout,
    ).pack(side="left", padx=10)
    ctk.CTkButton(
        bottom_frame,
        text="تعليق (F2)",
        fg_color="orange",
        command=self.hold_invoice,
    ).pack(side="left", padx=10)
    ctk.CTkButton(
        bottom_frame,
        text="استعلام (F4)",
        fg_color="blue",
        command=self.price_lookup,
    ).pack(side="left", padx=10)

    # ربط اختصارات الكيبورد
    self.bind("<F1>", lambda e: self.reset_cart())
    self.bind("<F2>", lambda e: self.hold_invoice())
    self.bind("<F3>", lambda e: self.show_held_invoices())
    self.bind("<F4>", lambda e: self.price_lookup())
    self.bind("<F5>", lambda e: self.checkout())
    self.bind("<Escape>", lambda e: self.show_login())

    self.update_cart_display()

  def add_to_cart(self, event=None):
    query = self.barcode_entry.get().strip()
    if not query:
      return

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM products WHERE barcode=? OR name LIKE ?",
        (query, f"%{query}%"),
    )
    product = c.fetchone()
    conn.close()

    if product:
      product = dict(product)
      # التحقق مما إذا كان المنتج موجوداً بالسلة
      for item in self.cart:
        if item["id"] == product["id"]:
          item["qty"] += 1
          break
      else:
        self.cart.append({
            "id": product["id"],
            "barcode": product["barcode"],
            "name": product["name"],
            "price": product["price"],
            "qty": 1,
        })
      self.barcode_entry.delete(0, "end")
      self.update_cart_display()
    else:
      messagebox.showwarning("تنبيه", "المنتج غير موجود في قاعدة البيانات!")

  def update_cart_display(self):
    for widget in self.cart_frame.winfo_children():
      widget.destroy()

    total = 0.0
    for idx, item in enumerate(self.cart):
      item_total = item["price"] * item["qty"]
      total += item_total

      row = ctk.CTkFrame(self.cart_frame)
      row.pack(fill="x", pady=2)

      ctk.CTkLabel(row, text=item["name"], width=200, anchor="w").pack(
          side="right", padx=5
      )
      ctk.CTkLabel(row, text=f"{item['price']} ج.م", width=100).pack(
          side="right", padx=5
      )
      ctk.CTkLabel(row, text=f"الكمية: {item['qty']}", width=100).pack(
          side="right", padx=5
      )
      ctk.CTkLabel(
          row, text=f"{item_total:.2f} ج.م", width=100, font=ctk.CTkFont(weight="bold")
      ).pack(side="right", padx=5)

      ctk.CTkButton(
          row,
          text="X",
          width=30,
          fg_color="red",
          command=lambda i=idx: self.remove_item(i),
      ).pack(side="left", padx=5)

    self.total_label.configure(text=f"الإجمالي: {total:.2f} ج.م")

  def remove_item(self, index):
    del self.cart[index]
    self.update_cart_display()

  def reset_cart(self):
    self.cart = []
    self.update_cart_display()

  def price_lookup(self):
    query = self.barcode_entry.get().strip()
    if not query:
      messagebox.showinfo("استعلام", "يرجى كتابة الباركود أو اسم المنتج أولاً")
      return
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM products WHERE barcode=? OR name LIKE ?",
        (query, f"%{query}%"),
    )
    product = c.fetchone()
    conn.close()

    if product:
      p = dict(product)
      messagebox.showinfo(
          "بيانات المنتج",
          f"الاسم: {p['name']}\nالسعر: {p['price']} ج.م\nالمخزون"
          f" المتبقي: {p['quantity']}",
      )
    else:
      messagebox.showerror("خطأ", "المنتج غير موجود!")

  def hold_invoice(self):
    if not self.cart:
      return
    self.held_invoices.append(list(self.cart))
    self.reset_cart()
    messagebox.showinfo("تم", "تم تعليق الفاتورة بنجاح!")

  def show_held_invoices(self):
    if not self.held_invoices:
      messagebox.showinfo("الفواتير المعلقة", "لا توجد فواتير معلقة حالياً.")
      return
    # استرجاع أول فاتورة معلقة كمثال
    self.cart = self.held_invoices.pop(0)
    self.update_cart_display()

  def checkout(self):
    if not self.cart:
      return
    total = sum(item["price"] * item["qty"] for item in self.cart)
    inv_num = f"INV-{int(datetime.now().timestamp())}"

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO invoices (invoice_number, date, total, user) VALUES (?, ?,"
        " ?, ?)",
        (inv_num, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), total, "cashier"),
    )
    inv_id = c.lastrowid

    for item in self.cart:
      c.execute(
          "INSERT INTO invoice_items (invoice_id, product_id, barcode, name,"
          " quantity, price, total) VALUES (?, ?, ?, ?, ?, ?, ?)",
          (
              inv_id,
              item["id"],
              item["barcode"],
              item["name"],
              item["qty"],
              item["price"],
              item["price"] * item["qty"],
          ),
      )
      c.execute(
          "UPDATE products SET quantity = quantity - ? WHERE id = ?",
          (item["qty"], item["id"]),
      )

    conn.commit()
    conn.close()

    messagebox.showinfo(
        "تمت العملية", f"تم طباعة الفاتورة رقم: {inv_num}\nالإجمالي: {total} ج.م"
    )
    self.reset_cart()

  # -------------------------------------------------------------
  # واجهة المدير
  # -------------------------------------------------------------
  def show_admin_dashboard(self):
    self.clear_screen()

    tabview = ctk.CTkTabview(self)
    tabview.pack(fill="both", expand=True, padx=10, pady=10)

    tabview.add("إدارة المنتجات والمخزون")
    tabview.add("إدارة الموردين")
    tabview.add("الفواتير والمبيعات")
    tabview.add("التحصيل اليومي (الورديات)")

    # 1. قسم المنتجات
    prod_tab = tabview.tab("إدارة المنتجات والمخزون")
    ctk.CTkLabel(
        prod_tab,
        text="إضافة / تعديل منتج",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(pady=5)

    f1 = ctk.CTkFrame(prod_tab)
    f1.pack(fill="x", padx=10, pady=5)

    name_e = ctk.CTkEntry(f1, placeholder_text="اسم المنتج")
    name_e.pack(side="right", padx=5)
    bar_e = ctk.CTkEntry(f1, placeholder_text="الباركود")
    bar_e.pack(side="right", padx=5)
    price_e = ctk.CTkEntry(f1, placeholder_text="سعر البيع")
    price_e.pack(side="right", padx=5)
    qty_e = ctk.CTkEntry(f1, placeholder_text="الكمية")
    qty_e.pack(side="right", padx=5)

    def save_product():
      conn = get_db_connection()
      c = conn.cursor()
      c.execute(
          "INSERT INTO products (name, barcode, price, quantity) VALUES (?, ?,"
          " ?, ?)",
          (
              name_e.get(),
              bar_e.get(),
              float(price_e.get() or 0),
              int(qty_e.get() or 0),
          ),
      )
      conn.commit()
      conn.close()
      messagebox.showinfo("تم", "تم حفظ المنتج بنجاح!")

    ctk.CTkButton(
        f1, text="حفظ المنتج", fg_color="green", command=save_product
    ).pack(side="right", padx=10)

    # زر الخروج والعودة لتسجيل الدخول
    ctk.CTkButton(
        self, text="تسجيل الخروج", fg_color="red", command=self.show_login
    ).pack(pady=5)


if __name__ == "__main__":
  init_db()
  app = POSApp()
  app.mainloop()
