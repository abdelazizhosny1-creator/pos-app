import tkinter as ttk
from tkinter import messagebox, ttk
import sqlite3
import datetime
import os
import sys
from PIL import Image, ImageTk

DB_NAME = "pos_database.db"

def resource_path(relative_path):
    """ الحصول على المسار الصحيح للصورة والموارد عند تشغيل ملف الـ EXE """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            barcode TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            total_amount REAL NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            barcode TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            qty INTEGER NOT NULL,
            total REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales (id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ("6221000123456", "حليب طازج 1 لتر", 35.0, 50),
            ("6221000654321", "أرز مصري 1 كجم", 30.0, 100),
            ("6221000999999", "زيت عباد الشمس", 65.0, 30),
            ("12345", "منتج تجريبي 1", 10.0, 20),
            ("67890", "منتج تجريبي 2", 15.5, 40)
        ]
        cursor.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", sample_products)
        conn.commit()
        
    conn.close()

class POSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("نظام نقاط البيع وإدارة المخزون - POS")
        self.root.geometry("1050x700")
        
        init_db()
        self.cart = []
        
        # --- إضافة خلفية الصورة ---
        bg_path = resource_path("bg.jpg")
        if os.path.exists(bg_path):
            try:
                self.bg_image_original = Image.open(bg_path)
                self.bg_photo = ImageTk.PhotoImage(self.bg_image_original.resize((1050, 700), Image.Resampling.LANCZOS))
                self.bg_label = ttk.Label(self.root, image=self.bg_photo)
                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            except Exception as e:
                print(f"خطأ في تحميل صورة الخلفية: {e}")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.sale_tab = ttk.Frame(self.notebook)
        self.product_tab = ttk.Frame(self.notebook)
        self.invoices_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.sale_tab, text=" شاشة البيع (الكاشير) ")
        self.notebook.add(self.product_tab, text=" إدارة المنتجات والمخزون ")
        self.notebook.add(self.invoices_tab, text=" سجل الفواتير والتعديل ")
        
        self.setup_sale_ui()
        self.setup_product_ui()
        self.setup_invoices_ui()
        
    # --- شاشة البيع ---
    def setup_sale_ui(self):
        top_frame = ttk.LabelFrame(self.sale_tab, text="مسح / أدخل الباركود", padding=10)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(top_frame, text="الباركود:").pack(side="right", padx=5)
        self.barcode_entry = ttk.Entry(top_frame, font=("Arial", 14))
        self.barcode_entry.pack(side="right", fill="x", expand=True, padx=5)
        self.barcode_entry.bind("<Return>", lambda event: self.add_to_cart())
        self.barcode_entry.focus()
        
        add_btn = ttk.Button(top_frame, text="إضافة للعملية", command=self.add_to_cart)
        add_btn.pack(side="left", padx=5)

        tree_frame = ttk.Frame(self.sale_tab, padding=10)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        columns = ("barcode", "name", "price", "qty", "total")
        self.cart_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)
        self.cart_tree.heading("barcode", text="الباركود")
        self.cart_tree.heading("name", text="اسم المنتج")
        self.cart_tree.heading("price", text="السعر")
        self.cart_tree.heading("qty", text="الكمية")
        self.cart_tree.heading("total", text="الإجمالي")
        
        self.cart_tree.column("barcode", width=120, anchor="center")
        self.cart_tree.column("name", width=250, anchor="right")
        self.cart_tree.column("price", width=100, anchor="center")
        self.cart_tree.column("qty", width=80, anchor="center")
        self.cart_tree.column("total", width=100, anchor="center")
        
        self.cart_tree.pack(fill="both", expand=True)

        bottom_frame = ttk.Frame(self.sale_tab, padding=10)
        bottom_frame.pack(fill="x", padx=10, pady=10)
        
        self.total_label = ttk.Label(bottom_frame, text="الإجمالي: 0.00 ج.م", font=("Arial", 18, "bold"), foreground="green")
        self.total_label.pack(side="right", padx=10)
        
        checkout_btn = ttk.Button(bottom_frame, text="إتمام عملية البيع (طباعة)", command=self.checkout)
        checkout_btn.pack(side="left", padx=5)
        
        clear_btn = ttk.Button(bottom_frame, text="إلغاء الفاتورة", command=self.clear_cart)
        clear_btn.pack(side="left", padx=5)

    def add_to_cart(self):
        barcode = self.barcode_entry.get().strip()
        if not barcode:
            return
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name, price, stock FROM products WHERE barcode = ?", (barcode,))
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            messagebox.showwarning("غير موجود", "المنتج غير مسجل في قاعدة البيانات!")
            self.barcode_entry.delete(0, ttk.END)
            return
            
        name, price, stock = product
        current_in_cart = sum(item['qty'] for item in self.cart if item['barcode'] == barcode)
        if current_in_cart + 1 > stock:
            messagebox.showerror("نفاد المخزون", f"الكمية المتاحة في المخزن هي {stock} فقط!")
            self.barcode_entry.delete(0, ttk.END)
            return

        for item in self.cart:
            if item['barcode'] == barcode:
                item['qty'] += 1
                item['total'] = item['qty'] * item['price']
                break
        else:
            self.cart.append({'barcode': barcode, 'name': name, 'price': price, 'qty': 1, 'total': price})
            
        self.update_cart_tree()
        self.barcode_entry.delete(0, ttk.END)

    def update_cart_tree(self):
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)
            
        grand_total = 0.0
        for item in self.cart:
            self.cart_tree.insert('', 'end', values=(
                item['barcode'], item['name'], f"{item['price']:.2f}", item['qty'], f"{item['total']:.2f}"
            ))
            grand_total += item['total']
            
        self.total_label.config(text=f"الإجمالي: {grand_total:.2f} ج.م")

    def clear_cart(self):
        self.cart = []
        self.update_cart_tree()

    def checkout(self):
        if not self.cart:
            messagebox.showwarning("تنبيه", "السلة فارغة!")
            return
            
        grand_total = sum(item['total'] for item in self.cart)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("INSERT INTO sales (timestamp, total_amount) VALUES (?, ?)", (now, grand_total))
        sale_id = cursor.lastrowid
        
        for item in self.cart:
            cursor.execute("INSERT INTO sale_items (sale_id, barcode, name, price, qty, total) VALUES (?, ?, ?, ?, ?, ?)",
                           (sale_id, item['barcode'], item['name'], item['price'], item['qty'], item['total']))
            cursor.execute("UPDATE products SET stock = stock - ? WHERE barcode = ?", (item['qty'], item['barcode']))
            
        conn.commit()
        conn.close()
        
        messagebox.showinfo("تم بنجاح", f"تم تسجيل الفاتورة رقم #{sale_id} بنجاح!\nالإجمالي: {grand_total:.2f} ج.م")
        self.clear_cart()
        self.load_products_list()
        self.load_invoices_list()

    # --- شاشة إدارة المنتجات ---
    def setup_product_ui(self):
        form_frame = ttk.LabelFrame(self.product_tab, text="إضافة / تعديل منتج", padding=10)
        form_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(form_frame, text="الباركود:").grid(row=0, column=3, padx=5, pady=5, sticky="e")
        self.p_barcode = ttk.Entry(form_frame, font=("Arial", 11))
        self.p_barcode.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        ttk.Label(form_frame, text="اسم المنتج:").grid(row=0, column=1, padx=5, pady=5, sticky="e")
        self.p_name = ttk.Entry(form_frame, font=("Arial", 11))
        self.p_name.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        
        ttk.Label(form_frame, text="السعر:").grid(row=1, column=3, padx=5, pady=5, sticky="e")
        self.p_price = ttk.Entry(form_frame, font=("Arial", 11))
        self.p_price.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        
        ttk.Label(form_frame, text="الكمية:").grid(row=1, column=1, padx=5, pady=5, sticky="e")
        self.p_stock = ttk.Entry(form_frame, font=("Arial", 11))
        self.p_stock.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        
        save_btn = ttk.Button(form_frame, text="حفظ / تحديث المنتج", command=self.save_product)
        save_btn.grid(row=2, column=0, columnspan=4, pady=10)

        list_frame = ttk.LabelFrame(self.product_tab, text="قائمة المنتجات بالمخزن", padding=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        cols = ("barcode", "name", "price", "stock")
        self.prod_tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        self.prod_tree.heading("barcode", text="الباركود")
        self.prod_tree.heading("name", text="اسم المنتج")
        self.prod_tree.heading("price", text="السعر (ج.م)")
        self.prod_tree.heading("stock", text="الكمية المتاحة")
        
        self.prod_tree.column("barcode", width=150, anchor="center")
        self.prod_tree.column("name", width=300, anchor="right")
        self.prod_tree.column("price", width=120, anchor="center")
        self.prod_tree.column("stock", width=120, anchor="center")
        
        self.prod_tree.pack(fill="both", expand=True)
        self.load_products_list()

    def save_product(self):
        barcode = self.p_barcode.get().strip()
        name = self.p_name.get().strip()
        price = self.p_price.get().strip()
        stock = self.p_stock.get().strip()
        
        if not (barcode and name and price and stock):
            messagebox.showwarning("خطأ", "يرجى ملء جميع الحقول!")
            return
            
        try:
            price_val = float(price)
            stock_val = int(stock)
        except ValueError:
            messagebox.showerror("خطأ", "السعر يجب أن يكون رقماً، والكمية عدداً صحيحاً!")
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO products (barcode, name, price, stock)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(barcode) DO UPDATE SET
                name=excluded.name,
                price=excluded.price,
                stock=stock + excluded.stock
        ''', (barcode, name, price_val, stock_val))
        conn.commit()
        conn.close()

        messagebox.showinfo("نجاح", "تم حفظ / تحديث المنتج بنجاح!")
        self.p_barcode.delete(0, ttk.END)
        self.p_name.delete(0, ttk.END)
        self.p_price.delete(0, ttk.END)
        self.p_stock.delete(0, ttk.END)
        self.load_products_list()

    def load_products_list(self):
        for item in self.prod_tree.get_children():
            self.prod_tree.delete(item)
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT barcode, name, price, stock FROM products")
        for row in cursor.fetchall():
            self.prod_tree.insert('', 'end', values=(row[0], row[1], f"{row[2]:.2f}", row[3]))
        conn.close()

    # --- شاشة سجل الفواتير ---
    def setup_invoices_ui(self):
        main_frame = ttk.Frame(self.invoices_tab, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        left_frame = ttk.LabelFrame(main_frame, text="قائمة الفواتير المسجلة", padding=10)
        left_frame.pack(side="right", fill="both", expand=True, padx=5)
        
        inv_cols = ("id", "time", "total")
        self.inv_tree = ttk.Treeview(left_frame, columns=inv_cols, show="headings")
        self.inv_tree.heading("id", text="رقم الفاتورة")
        self.inv_tree.heading("time", text="التاريخ والوقت")
        self.inv_tree.heading("total", text="الإجمالي")
        
        self.inv_tree.column("id", width=80, anchor="center")
        self.inv_tree.column("time", width=180, anchor="center")
        self.inv_tree.column("total", width=100, anchor="center")
        
        self.inv_tree.pack(fill="both", expand=True)
        self.inv_tree.bind("<<TreeviewSelect>>", self.on_invoice_select)
        
        right_frame = ttk.LabelFrame(main_frame, text="تفاصيل الفاتورة المختارة", padding=10)
        right_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        items_cols = ("name", "price", "qty", "total")
        self.inv_items_tree = ttk.Treeview(right_frame, columns=items_cols, show="headings")
        self.inv_items_tree.heading("name", text="الصنف")
        self.inv_items_tree.heading("price", text="السعر")
        self.inv_items_tree.heading("qty", text="الكمية")
        self.inv_items_tree.heading("total", text="الإجمالي")
        
        self.inv_items_tree.column("name", width=150, anchor="right")
        self.inv_items_tree.column("price", width=70, anchor="center")
        self.inv_items_tree.column("qty", width=60, anchor="center")
        self.inv_items_tree.column("total", width=80, anchor="center")
        
        self.inv_items_tree.pack(fill="both", expand=True, pady=5)
        
        delete_inv_btn = ttk.Button(right_frame, text="إلغاء/حذف الفاتورة وإعادة البضاعة للمخزن", command=self.delete_invoice)
        delete_inv_btn.pack(fill="x", pady=5)
        
        self.load_invoices_list()

    def load_invoices_list(self):
        for item in self.inv_tree.get_children():
            self.inv_tree.delete(item)
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, total_amount FROM sales ORDER BY id DESC")
        for row in cursor.fetchall():
            self.inv_tree.insert('', 'end', values=(f"#{row[0]}", row[1], f"{row[2]:.2f} ج.م"))
        conn.close()

    def on_invoice_select(self, event):
        selected = self.inv_tree.selection()
        if not selected:
            return
            
        item_values = self.inv_tree.item(selected[0], "values")
        sale_id = item_values[0].replace("#", "")
        
        for item in self.inv_items_tree.get_children():
            self.inv_items_tree.delete(item)
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT name, price, qty, total FROM sale_items WHERE sale_id = ?", (sale_id,))
        for row in cursor.fetchall():
            self.inv_items_tree.insert('', 'end', values=(row[0], f"{row[1]:.2f}", row[2], f"{row[3]:.2f}"))
        conn.close()

    def delete_invoice(self):
        selected = self.inv_tree.selection()
        if not selected:
            messagebox.showwarning("تنبيه", "يرجى اختيار فاتورة أولاً!")
            return
            
        item_values = self.inv_tree.item(selected[0], "values")
        sale_id = item_values[0].replace("#", "")
        
        confirm = messagebox.askyesno("تأكيد", f"هل أنت تأكد من إلغاء/حذف الفاتورة #{sale_id}؟\nسيتم إرجاع الأصناف المبيعة إلى المخزن أوتوماتيكياً.")
        if not confirm:
            return
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT barcode, qty FROM sale_items WHERE sale_id = ?", (sale_id,))
        items = cursor.fetchall()
        for barcode, qty in items:
            cursor.execute("UPDATE products SET stock = stock + ? WHERE barcode = ?", (qty, barcode))
            
        cursor.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
        cursor.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
        
        conn.commit()
        conn.close()
        
        messagebox.showinfo("نجاح", f"تم إلغاء الفاتورة #{sale_id} وإعادة الكميات للمخزن بنجاح!")
        self.load_invoices_list()
        self.load_products_list()
        for item in self.inv_items_tree.get_children():
            self.inv_items_tree.delete(item)

if __name__ == "__main__":
    root = ttk.Tk()
    app = POSApp(root)
    root.mainloop()
