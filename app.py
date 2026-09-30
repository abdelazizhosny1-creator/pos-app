import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime

# ==================== 1. تهيئة قاعدة البيانات SQLite ====================
def init_db():
    conn = sqlite3.connect("pos_system.db")
    cursor = conn.cursor()
    
    # جدول المنتجات والمخزون
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            barcode TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL,
            supplier TEXT
        )
    ''')
    
    # جدول الموردين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT
        )
    ''')
    
    # جدول الفواتير والمبيعات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            total_amount REAL
        )
    ''')
    
    # إضافة منتجات افتراضية للتجربة إذا كان الجدول فارغاً
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO products VALUES ('101', 'منتج A', 50.0, 100, 'مورد العالمية')")
        cursor.execute("INSERT INTO products VALUES ('102', 'منتج B', 25.5, 50, 'مورد النور')")
        cursor.execute("INSERT INTO suppliers (name, phone) VALUES ('مورد العالمية', '01000000000')")
        cursor.execute("INSERT INTO suppliers (name, phone) VALUES ('مورد النور', '01100000000')")
        
    conn.commit()
    conn.close()

init_db()

# ==================== 2. الواجهة الرئيسية والتنقل ====================
class POSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("نظام POS المبيعات والمخازن المتكامل")
        self.geometry("1024x700")
        
        # قائمة الفواتير المعلقة
        self.held_invoices = []
        
        # إنشاء دفتر التبويبات (الكاشير - المدير)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        
        # تبويب الكاشير
        self.cashier_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.cashier_frame, text="واجهة الكاشير")
        
        # تبويب الإدارة
        self.admin_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.admin_frame, text="لوحة التحكم والمدير")
        
        # بناء الواجهات
        self.build_cashier_ui()
        self.build_admin_ui()
        
        #ربط اختصارات لوحة المفاتيح
        self.bind("<F1>", lambda e: self.new_invoice())
        self.bind("<F2>", lambda e: self.hold_invoice())
        self.bind("<F3>", lambda e: self.retrieve_held_invoice())
        self.bind("<F4>", lambda e: self.price_lookup())
        self.bind("<F5>", lambda e: self.print_invoice())
        self.bind("<Escape>", lambda e: self.exit_app())

    # ==================== 3. واجهة الكاشير (الجزء الأول) ====================
    def build_cashier_ui(self):
        # شريط الاختصارات العلوي
        btn_frame = ttk.Frame(self.cashier_frame)
        btn_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(btn_frame, text="[F1] فاتورة جديدة", command=self.new_invoice).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="[F2] تعليق الفاتورة", command=self.hold_invoice).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="[F3] الفواتير المعلقة", command=self.retrieve_held_invoice).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="[F4] استعلام سعر", command=self.price_lookup).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="[F5] طباعة وإغلاق", command=self.print_invoice).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="[Esc] خروج", command=self.exit_app).pack(side="right", padx=5)

        # جدول الفاتورة
        columns = ("barcode", "name", "price", "qty", "total")
        self.cart_tree = ttk.Treeview(self.cashier_frame, columns=columns, show="headings")
        self.cart_tree.heading("barcode", text="الباركويد")
        self.cart_tree.heading("name", text="اسم المنتج")
        self.cart_tree.heading("price", text="السعر")
        self.cart_tree.heading("qty", text="الكمية")
        self.cart_tree.heading("total", text="الإجمالي")
        self.cart_tree.pack(fill="both", expand=True, padx=10, pady=5)

        # شريط إدخال الباركويد والإجمالي
        bottom_frame = ttk.Frame(self.cashier_frame)
        bottom_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(bottom_frame, text="مسح الباركويد:", font=("Arial", 12)).pack(side="left", padx=5)
        self.barcode_entry = ttk.Entry(bottom_frame, font=("Arial", 12))
        self.barcode_entry.pack(side="left", padx=5)
        self.barcode_entry.bind("<Return>", self.add_product_by_barcode)
        self.barcode_entry.focus()

        self.total_label = ttk.Label(bottom_frame, text="الإجمالي: 0.00 ج.م", font=("Arial", 16, "bold"), foreground="green")
        self.total_label.pack(side="right", padx=10)

    def add_product_by_barcode(self, event=None):
        barcode = self.barcode_entry.get().strip()
        if not barcode:
            return

        conn = sqlite3.connect("pos_system.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name, price FROM products WHERE barcode=?", (barcode,))
        product = cursor.fetchone()
        conn.close()

        if product:
            name, price = product
            # فحص إذا كان الصنف موجود بالجدول مسبقاً
            for item in self.cart_tree.get_children():
                vals = self.cart_tree.item(item, "values")
                if vals[0] == barcode:
                    qty = int(vals[3]) + 1
                    total = qty * price
                    self.cart_tree.item(item, values=(barcode, name, price, qty, total))
                    self.update_total()
                    self.barcode_entry.delete(0, tk.END)
                    return

            self.cart_tree.insert("", "end", values=(barcode, name, price, 1, price))
            self.update_total()
        else:
            messagebox.showwarning("تنبيه", "المنتج غير موجود في قاعدة البيانات!")
        
        self.barcode_entry.delete(0, tk.END)

    def update_total(self):
        grand_total = 0.0
        for item in self.cart_tree.get_children():
            grand_total += float(self.cart_tree.item(item, "values")[4])
        self.total_label.config(text=f"الإجمالي: {grand_total:.2f} ج.م")

    def new_invoice(self):
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
        self.update_total()

    def hold_invoice(self):
        items = [self.cart_tree.item(child, "values") for child in self.cart_tree.get_children()]
        if items:
            self.held_invoices.append(items)
            self.new_invoice()
            messagebox.showinfo("نجاح", "تم تعليق الفاتورة بنجاح.")

    def retrieve_held_invoice(self):
        if self.held_invoices:
            self.new_invoice()
            items = self.held_invoices.pop()
            for item in items:
                self.cart_tree.insert("", "end", values=item)
            self.update_total()
        else:
            messagebox.showwarning("تنبيه", "لا توجد فواتير معلقة!")

    def price_lookup(self):
        barcode = simpledialog.askstring("استعلام سعر", "ادخل أو امسح الباركويد:")
        if barcode:
            conn = sqlite3.connect("pos_system.db")
            cursor = conn.cursor()
            cursor.execute("SELECT name, price, stock FROM products WHERE barcode=?", (barcode,))
            product = cursor.fetchone()
            conn.close()
            if product:
                messagebox.showinfo("تفاصيل المنتج", f"الاسم: {product[0]}\nالسعر: {product[1]} ج.م\nالمخزون المتبقي: {product[2]}")
            else:
                messagebox.showerror("خطأ", "المنتج غير مسجل!")

    def print_invoice(self):
        items = self.cart_tree.get_children()
        if not items:
            return

        grand_total = sum(float(self.cart_tree.item(i, "values")[4]) for i in items)
        
        # حفظ الفاتورة في المبيعات وتحديث المخزون
        conn = sqlite3.connect("pos_system.db")
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO sales (timestamp, total_amount) VALUES (?, ?)", (now, grand_total))
        
        for item in items:
            vals = self.cart_tree.item(item, "values")
            barcode, qty = vals[0], int(vals[3])
            cursor.execute("UPDATE products SET stock = stock - ? WHERE barcode=?", (qty, barcode))
            
        conn.commit()
        conn.close()

        messagebox.showinfo("طباعة الفاتورة", f"تم إغلاق الفاتورة بقيمة {grand_total:.2f} ج.م\nوفتح درج النقدية تلقائياً.")
        self.new_invoice()
        self.refresh_admin_data()

    def exit_app(self):
        if messagebox.askyesno("خروج", "هل تريد الخروج من البرنامج؟"):
            self.destroy()

    # ==================== 4. واجهة المدير والتحصيل (الجزء الثاني) ====================
    def build_admin_ui(self):
        admin_notebook = ttk.Notebook(self.admin_frame)
        admin_notebook.pack(fill="both", expand=True)

        # تبويب إدارة المخزون
        stock_tab = ttk.Frame(admin_notebook)
        admin_notebook.add(stock_tab, text="المخزون والمنتجات")

        self.stock_tree = ttk.Treeview(stock_tab, columns=("barcode", "name", "price", "stock", "supplier"), show="headings")
        for col, txt in zip(("barcode", "name", "price", "stock", "supplier"), ("الباركويد", "الاسم", "السعر", "المتبقي", "المورد")):
            self.stock_tree.heading(col, text=txt)
        self.stock_tree.pack(fill="both", expand=True, padx=5, pady=5)

        btn_add = ttk.Button(stock_tab, text="إضافة / تعديل منتج", command=self.add_product_dialog)
        btn_add.pack(pady=5)

        # تبويب التحصيل اليومي / الورديات
        reports_tab = ttk.Frame(admin_notebook)
        admin_notebook.add(reports_tab, text="التحصيل اليومي والورديات")

        self.report_label = ttk.Label(reports_tab, text="", font=("Arial", 14))
        self.report_label.pack(pady=20)

        ttk.Button(reports_tab, text="تحديث تقرير الوردية", command=self.refresh_admin_data).pack()

        self.refresh_admin_data()

    def add_product_dialog(self):
        barcode = simpledialog.askstring("منتج جديد", "ادخل الباركويد:")
        if not barcode: return
        name = simpledialog.askstring("منتج جديد", "ادخل اسم المنتج:")
        price = float(simpledialog.askstring("منتج جديد", "ادخل السعر:") or 0)
        stock = int(simpledialog.askstring("منتج جديد", "ادخل الكمية بالمخزون:") or 0)
        supplier = simpledialog.askstring("منتج جديد", "اسم المورد:")

        conn = sqlite3.connect("pos_system.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?, ?)", (barcode, name, price, stock, supplier))
        conn.commit()
        conn.close()
        self.refresh_admin_data()

    def refresh_admin_data(self):
        # تحديث شجرة المخزون
        for i in self.stock_tree.get_children():
            self.stock_tree.delete(i)
        
        conn = sqlite3.connect("pos_system.db")
        cursor = conn.cursor()
        cursor.execute("SELECT barcode, name, price, stock, supplier FROM products")
        for row in cursor.fetchall():
            self.stock_tree.insert("", "end", values=row)

        # تحديث المبيعات والوردية
        cursor.execute("SELECT COUNT(*), SUM(total_amount) FROM sales")
        sales_data = cursor.fetchone()
        count = sales_data[0] or 0
        total_sum = sales_data[1] or 0.0
        conn.close()

        self.report_label.config(text=f"إجمالي فواتير الوردية: {count}\nإجمالي تحصيل المبيعات: {total_sum:.2f} ج.م")

if __name__ == "__main__":
    app = POSApp()
    app.mainloop()
