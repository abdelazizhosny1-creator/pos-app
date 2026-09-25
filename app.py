import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class AccountingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("(POS) نظام المحاسبة ونقطة البيع")
        self.root.geometry("900x650")
        self.root.configure(bg="#f4f6f9")

        # قاعدة بيانات مصغرة للمنتجات [الباركود: {اسم المنتج، السعر}]
        self.products_db = {
            "6221000123456": {"name": "حليب طازج 1 لتر", "price": 35.0},
            "6221000654321": {"name": "أرز مصري 1 كجم", "price": 30.0},
            "6221000999999": {"name": "زيت عباد الشمس", "price": 65.0},
            "12345": {"name": "منتج تجريبي 1", "price": 10.0},
            "67890": {"name": "منتج تجريبي 2", "price": 15.5}
        }

        # السلة الحالية
        self.cart = []
        self.total_amount = 0.0

        # إنشاء واجهة المستخدم
        self.create_widgets()

    def create_widgets(self):
        # عنوان التطبيق
        header_frame = tk.Frame(self.root, bg="#2c3e50", height=60)
        header_frame.pack(fill="x")
        
        title_label = tk.Label(header_frame, text="نظام المحاسبة ونقطة البيع (POS)", font=("Arial", 18, "bold"), fg="white", bg="#2c3e50")
        title_label.pack(pady=15)

        # الإطار الرئيسي
        main_frame = tk.Frame(self.root, bg="#f4f6f9")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # إطار إدخال الباركود والبحث
        input_frame = tk.LabelFrame(main_frame, text=" إضافة منتج ", font=("Arial", 12, "bold"), bg="#f4f6f9", fg="#2c3e50")
        input_frame.pack(fill="x", pady=10, ipady=5)

        tk.Label(input_frame, text="امسح أو اكتب الباركود:", font=("Arial", 11), bg="#f4f6f9").grid(row=0, column=0, padx=10, pady=10)
        self.barcode_entry = tk.Entry(input_frame, font=("Arial", 12), width=25)
        self.barcode_entry.grid(row=0, column=1, padx=10, pady=10)
        self.barcode_entry.bind("<Return>", lambda event: self.add_product_by_barcode())
        self.barcode_entry.focus()

        add_btn = tk.Button(input_frame, text="إضافة للسلة", font=("Arial", 11, "bold"), bg="#27ae60", fg="white", command=self.add_product_by_barcode)
        add_btn.grid(row=0, column=2, padx=10, pady=10)

        # جدول الفاتورة والسلة
        table_frame = tk.Frame(main_frame, bg="#f4f6f9")
        table_frame.pack(fill="both", expand=True, pady=10)

        columns = ("name", "price", "qty", "total")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=10)
        
        self.tree.heading("name", text="اسم المنتج")
        self.tree.heading("price", text="السعر")
        self.tree.heading("qty", text="الكمية")
        self.tree.heading("total", text="الإجمالي")

        self.tree.column("name", anchor="center", width=250)
        self.tree.column("price", anchor="center", width=120)
        self.tree.column("qty", anchor="center", width=100)
        self.tree.column("total", anchor="center", width=150)

        self.tree.pack(fill="both", expand=True)

        # إطار الإجمالي والأزرار
        footer_frame = tk.Frame(main_frame, bg="#f4f6f9")
        footer_frame.pack(fill="x", pady=10)

        self.total_label = tk.Label(footer_frame, text="الإجمالي: 0.00 ج.م", font=("Arial", 16, "bold"), fg="#c0392b", bg="#f4f6f9")
        self.total_label.pack(side="right", padx=10)

        pay_btn = tk.Button(footer_frame, text="إنهاء وتحصيل الفاتورة", font=("Arial", 12, "bold"), bg="#2980b9", fg="white", padx=20, pady=5, command=self.checkout)
        pay_btn.pack(side="left", padx=10)

        clear_btn = tk.Button(footer_frame, text="إلغاء الفاتورة", font=("Arial", 12, "bold"), bg="#e74c3c", fg="white", padx=15, pady=5, command=self.clear_cart)
        clear_btn.pack(side="left", padx=10)

    def add_product_by_barcode(self):
        barcode = self.barcode_entry.get().strip()
        if not barcode:
            return

        if barcode in self.products_db:
            product = self.products_db[barcode]
            # البحث إذا كان المنتج موجوداً مسبقاً في السلة لزيادة الكمية
            found = False
            for item in self.cart:
                if item["barcode"] == barcode:
                    item["qty"] += 1
                    item["total"] = item["qty"] * item["price"]
                    found = True
                    break

            if not found:
                self.cart.append({
                    "barcode": barcode,
                    "name": product["name"],
                    "price": product["price"],
                    "qty": 1,
                    "total": product["price"]
                })

            self.update_cart_display()
            self.barcode_entry.delete(0, tk.END)
        else:
            messagebox.showerror("خطأ", "المنتج غير موجود في قاعدة البيانات!")
            self.barcode_entry.delete(0, tk.END)

    def update_cart_display(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        self.total_amount = 0.0
        for item in self.cart:
            self.tree.insert("", tk.END, values=(item["name"], f"{item['price']:.2f}", item["qty"], f"{item['total']:.2f}"))
            self.total_amount += item["total"]

        self.total_label.config(text=f"الإجمالي: {self.total_amount:.2f} ج.م")

    def checkout(self):
        if not self.cart:
            messagebox.showwarning("تنبيه", "السلة فارغة!")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = f"تم تحصيل الفاتورة بنجاح!\nالمبلغ الإجمالي: {self.total_amount:.2f} ج.م\nالتاريخ: {now}"
        messagebox.showinfo("نجاح العملية", msg)
        self.clear_cart()

    def clear_cart(self):
        self.cart = []
        self.update_cart_display()

if __name__ == "__main__":
    root = tk.Tk()
    app = AccountingApp(root)
    root.mainloop()
