# -*- coding: utf-8 -*-
"""
DH STORE Store - Behavioral Entropy E-Commerce Project
--------------------------------------------------------
A simple Flask + SQLite DH STORE built for a college project
(Behavioral Entropy Analysis for E-Commerce Platforms).

How to run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
Admin dashboard: http://127.0.0.1:5000/admin/login
"""
import csv
import io
import os
import re
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash

from models import (
    db, Customer, Product, Address, CartItem, WishlistItem, Order, OrderItem,
    LoginLog, ProductView, SearchLog, CartEvent, Admin,
    generate_customer_id, generate_order_id
)
from seed_data import seed_products, seed_admin

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)


@app.template_filter("ist_datetime")
def ist_datetime(value):
    """Display stored UTC-naive timestamps as India Standard Time (IST)."""
    if not value:
        return ""
    return (value + timedelta(hours=5, minutes=30)).strftime("%d %b %Y, %I:%M %p")
app.secret_key = "dh-store-college-project-secret-key"  # change this if you deploy it anywhere
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "data", "store.db")

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# Pages that do NOT need the user to be logged in first.
PUBLIC_ENDPOINTS = {
    "login", "login_submit",
    "signup", "signup_submit",
    "admin_login", "admin_logout", "admin_dashboard", "admin_export_csv",
    "static",
}


# ---------------------------------------------------------------------------
# Small helper functions
# ---------------------------------------------------------------------------

def get_logged_in_customer():
    customer_id = session.get("customer_id")
    if not customer_id:
        return None
    return Customer.query.get(customer_id)


def is_valid_email(value):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value or ""))


def is_valid_mobile(value):
    return bool(re.match(r"^[6-9]\d{9}$", (value or "").strip()))


def get_cart_count(customer_id):
    total = 0
    for item in CartItem.query.filter_by(customer_id=customer_id).all():
        total += item.quantity
    return total


def get_device_type():
    user_agent = (request.headers.get("User-Agent") or "").lower()
    for word in ["mobi", "android", "iphone", "ipad"]:
        if word in user_agent:
            return "Mobile"
    return "Desktop"


# Every page (except the public ones above) needs the user to be logged in.
# This makes the SIGN UP / LOG IN page the first thing a new visitor sees.
@app.before_request
def check_login():
    if request.endpoint is None:
        return
    if request.endpoint in PUBLIC_ENDPOINTS:
        return
    if request.endpoint.startswith("admin"):
        return
    if not session.get("customer_id"):
        return redirect(url_for("login"))


@app.context_processor
def inject_common_data():
    customer = get_logged_in_customer()
    cart_count = get_cart_count(customer.customer_id) if customer else 0
    wishlist_count = WishlistItem.query.filter_by(customer_id=customer.customer_id).count() if customer else 0
    categories = [row[0] for row in db.session.query(Product.category).distinct().order_by(Product.category)]
    return {
        "current_customer": customer,
        "cart_count": cart_count,
        "wishlist_count": wishlist_count,
        "all_categories": categories,
    }


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Sign Up
# ---------------------------------------------------------------------------

@app.route("/signup", methods=["GET"])
def signup():
    if session.get("customer_id"):
        return redirect(url_for("index"))
    return render_template("signup.html")


@app.route("/signup", methods=["POST"])
def signup_submit():
    name = request.form.get("name", "").strip()
    identifier = request.form.get("identifier", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name:
        flash("Please enter your name.", "error")
        return redirect(url_for("signup"))

    if not (is_valid_mobile(identifier) or is_valid_email(identifier)):
        flash("Enter a valid 10-digit mobile number or a valid email address.", "error")
        return redirect(url_for("signup"))

    already_exists = Customer.query.filter(
        (Customer.mobile == identifier) | (Customer.email == identifier)
    ).first()
    if already_exists:
        flash("An account already exists. Please log in.", "error")
        return redirect(url_for("login"))

    if len(password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return redirect(url_for("signup"))

    if password != confirm_password:
        flash("Password and Confirm Password do not match.", "error")
        return redirect(url_for("signup"))

    new_customer = Customer(
        customer_id=generate_customer_id(),
        name=name,
        mobile=identifier if is_valid_mobile(identifier) else None,
        email=identifier if is_valid_email(identifier) else None,
        password_hash=generate_password_hash(password),
    )
    db.session.add(new_customer)
    db.session.commit()

    flash("Account created successfully. Please log in.", "success")
    return redirect(url_for("login"))


# Login / Logout
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET"])
def login():
    if session.get("customer_id"):
        return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_submit():
    identifier = request.form.get("identifier", "").strip()
    password = request.form.get("password", "")

    customer = Customer.query.filter(
        (Customer.mobile == identifier) | (Customer.email == identifier)
    ).first()

    if not customer or not check_password_hash(customer.password_hash, password):
        flash("Invalid mobile/email or password.", "error")
        return redirect(url_for("login"))

    session["customer_id"] = customer.customer_id
    db.session.add(LoginLog(customer_id=customer.customer_id, device_type=get_device_type()))
    db.session.commit()

    flash("Welcome back, " + customer.name + "!", "success")
    return redirect(url_for("index"))


@app.route("/logout")
def logout():
    session.pop("customer_id", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Home page / product listing
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/home")
def home():
    if not session.get("customer_id"):
        return redirect(url_for("login"))
    if not session.get("customer_id"):
        return redirect(url_for("login"))

    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    products_query = Product.query
    if query:
        products_query = products_query.filter(Product.name.ilike("%" + query + "%"))
        customer = get_logged_in_customer()
        db.session.add(SearchLog(customer_id=customer.customer_id, search_query=query))
        db.session.commit()
    if category:
        products_query = products_query.filter_by(category=category)

    products = products_query.order_by(Product.name.asc()).all()
    return render_template("index.html", products=products, query=query, active_category=category)


@app.route("/product/<product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related_products = (Product.query.filter_by(category=product.category)
                         .filter(Product.product_id != product.product_id).limit(4).all())

    customer = get_logged_in_customer()
    view = ProductView(customer_id=customer.customer_id, product_id=product.product_id)
    db.session.add(view)
    db.session.commit()

    in_wishlist = WishlistItem.query.filter_by(
        customer_id=customer.customer_id, product_id=product.product_id).first() is not None

    return render_template("product.html", product=product, related_products=related_products,
                            in_wishlist=in_wishlist, view_id=view.id)


@app.route("/track/product-duration/<int:view_id>", methods=["POST"])
def track_product_duration(view_id):
    """Save time spent on a product page when the customer leaves it."""
    customer = get_logged_in_customer()
    view = ProductView.query.filter_by(id=view_id, customer_id=customer.customer_id).first()
    if not view:
        return {"ok": False}, 404

    data = request.get_json(silent=True) or {}
    try:
        seconds = float(data.get("duration_seconds", 0))
    except (TypeError, ValueError):
        seconds = 0
    view.duration_seconds = round(max(0.0, min(seconds, 3600.0)), 1)
    db.session.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

@app.route("/cart")
def cart_view():
    customer = get_logged_in_customer()
    items = CartItem.query.filter_by(customer_id=customer.customer_id).all()
    subtotal = 0
    for item in items:
        subtotal += item.product.price * item.quantity
    return render_template("cart.html", items=items, subtotal=subtotal)


@app.route("/cart/add/<product_id>", methods=["POST"])
def cart_add(product_id):
    product = Product.query.get_or_404(product_id)
    customer = get_logged_in_customer()

    selected_size = request.form.get("size", "").strip() or None
    options = product.purchase_options()

    if "Size" in options and selected_size not in options["Size"]:
        flash("Please select a size on the product page before adding it to the cart.", "warning")
        return redirect(url_for("product_detail", product_id=product_id))

    existing_item = CartItem.query.filter_by(
        customer_id=customer.customer_id,
        product_id=product_id,
        selected_size=selected_size
    ).first()

    if existing_item:
        existing_item.quantity += 1
    else:
        db.session.add(CartItem(
            customer_id=customer.customer_id,
            product_id=product_id,
            quantity=1,
            selected_size=selected_size
        ))

    db.session.add(CartEvent(customer_id=customer.customer_id, product_id=product_id))
    db.session.commit()

    flash("Added to cart.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/buy-now/<product_id>", methods=["POST"])
def buy_now(product_id):
    """Add one product to the cart and take the customer directly to checkout."""
    product = Product.query.get_or_404(product_id)
    customer = get_logged_in_customer()

    selected_size = request.form.get("size", "").strip() or None
    options = product.purchase_options()

    if "Size" in options and selected_size not in options["Size"]:
        flash("Please select a size on the product page before buying this product.", "warning")
        return redirect(url_for("product_detail", product_id=product_id))

    existing_item = CartItem.query.filter_by(
        customer_id=customer.customer_id,
        product_id=product_id,
        selected_size=selected_size
    ).first()

    if existing_item:
        existing_item.quantity += 1
    else:
        db.session.add(CartItem(
            customer_id=customer.customer_id,
            product_id=product_id,
            quantity=1,
            selected_size=selected_size
        ))

    db.session.add(CartEvent(customer_id=customer.customer_id, product_id=product_id))
    db.session.commit()

    return redirect(url_for("checkout"))


@app.route("/cart/update/<int:item_id>", methods=["POST"])
def cart_update(item_id):
    customer = get_logged_in_customer()
    item = CartItem.query.filter_by(id=item_id, customer_id=customer.customer_id).first_or_404()
    new_quantity = int(request.form.get("quantity", 1))
    if new_quantity < 1:
        new_quantity = 1
    if new_quantity > 10:
        new_quantity = 10
    item.quantity = new_quantity
    db.session.commit()
    return redirect(url_for("cart_view"))


@app.route("/cart/remove/<int:item_id>", methods=["POST"])
def cart_remove(item_id):
    customer = get_logged_in_customer()
    item = CartItem.query.filter_by(id=item_id, customer_id=customer.customer_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    flash("Removed from cart.", "success")
    return redirect(url_for("cart_view"))


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

@app.route("/wishlist")
def wishlist_view():
    customer = get_logged_in_customer()
    items = WishlistItem.query.filter_by(customer_id=customer.customer_id).all()
    return render_template("wishlist.html", items=items)


@app.route("/wishlist/add/<product_id>", methods=["POST"])
def wishlist_add(product_id):
    Product.query.get_or_404(product_id)
    customer = get_logged_in_customer()
    already_saved = WishlistItem.query.filter_by(customer_id=customer.customer_id, product_id=product_id).first()
    if not already_saved:
        db.session.add(WishlistItem(customer_id=customer.customer_id, product_id=product_id))
        db.session.commit()
        flash("Added to wishlist.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/wishlist/remove/<int:item_id>", methods=["POST"])
def wishlist_remove(item_id):
    customer = get_logged_in_customer()
    item = WishlistItem.query.filter_by(id=item_id, customer_id=customer.customer_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return redirect(request.referrer or url_for("wishlist_view"))


# ---------------------------------------------------------------------------
# Checkout (address form + Cash on Delivery only)
# ---------------------------------------------------------------------------

@app.route("/checkout", methods=["GET"])
def checkout():
    customer = get_logged_in_customer()
    items = CartItem.query.filter_by(customer_id=customer.customer_id).all()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart_view"))
    subtotal = 0
    for item in items:
        subtotal += item.product.price * item.quantity
    saved_addresses = Address.query.filter_by(customer_id=customer.customer_id).all()
    return render_template("checkout.html", items=items, subtotal=subtotal, saved_addresses=saved_addresses)


@app.route("/checkout", methods=["POST"])
def checkout_submit():
    customer = get_logged_in_customer()
    items = CartItem.query.filter_by(customer_id=customer.customer_id).all()
    if not items:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart_view"))

    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    line1 = request.form.get("line1", "").strip()
    line2 = request.form.get("line2", "").strip()
    city = request.form.get("city", "").strip()
    state = request.form.get("state", "").strip()
    pincode = request.form.get("pincode", "").strip()
    landmark = request.form.get("landmark", "").strip()

    if not (full_name and phone and line1 and city and state and pincode):
        flash("Please fill in all required address fields.", "error")
        return redirect(url_for("checkout"))
    if not re.match(r"^\d{6}$", pincode):
        flash("Enter a valid 6-digit pincode.", "error")
        return redirect(url_for("checkout"))
    if not re.match(r"^[6-9]\d{9}$", phone):
        flash("Enter a valid 10-digit phone number.", "error")
        return redirect(url_for("checkout"))

    if request.form.get("save_address"):
        db.session.add(Address(customer_id=customer.customer_id, full_name=full_name, phone=phone,
                                line1=line1, line2=line2, city=city, state=state,
                                pincode=pincode, landmark=landmark))

    subtotal = 0
    for item in items:
        subtotal += item.product.price * item.quantity

    new_order = Order(
        order_id=generate_order_id(),
        customer_id=customer.customer_id,
        full_name=full_name, phone=phone, line1=line1, line2=line2,
        city=city, state=state, pincode=pincode, landmark=landmark,
        payment_method="COD", total_amount=subtotal, status="Placed",
    )
    db.session.add(new_order)
    db.session.flush()

    for item in items:
        db.session.add(OrderItem(
            order_id=new_order.order_id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.product.price,
            selected_size=item.selected_size
        ))
        db.session.delete(item)

    db.session.commit()
    return redirect(url_for("order_success", order_id=new_order.order_id))


@app.route("/order/<order_id>/success")
def order_success(order_id):
    customer = get_logged_in_customer()
    order = Order.query.filter_by(order_id=order_id, customer_id=customer.customer_id).first_or_404()
    return render_template("order_success.html", order=order)


@app.route("/orders")
def orders_view():
    customer = get_logged_in_customer()
    orders = Order.query.filter_by(customer_id=customer.customer_id).order_by(Order.created_at.desc()).all()
    return render_template("orders.html", orders=orders)


# ---------------------------------------------------------------------------
# Admin dashboard
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    admin = Admin.query.filter_by(username=username).first()
    if not admin or not check_password_hash(admin.password_hash, password):
        flash("Invalid admin credentials.", "error")
        return redirect(url_for("admin_login"))

    session["admin_id"] = admin.id
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    return redirect(url_for("admin_login"))


def build_customer_metrics():
    """Works out the behavior numbers for each customer, used by the
    dashboard table and the CSV export."""
    all_metrics = []

    for customer in Customer.query.all():
        logins = LoginLog.query.filter_by(customer_id=customer.customer_id).all()
        views = (ProductView.query.filter_by(customer_id=customer.customer_id)
                 .order_by(ProductView.timestamp.asc()).all())
        search_count = SearchLog.query.filter_by(customer_id=customer.customer_id).count()
        cart_add_count = CartEvent.query.filter_by(customer_id=customer.customer_id).count()
        wishlist_count = WishlistItem.query.filter_by(customer_id=customer.customer_id).count()
        cart_count = get_cart_count(customer.customer_id)
        orders = Order.query.filter_by(customer_id=customer.customer_id).all()

        visited_ids = []
        for v in views:
            if v.product_id not in visited_ids:
                visited_ids.append(v.product_id)

        # Average time actually spent on product pages, captured by the browser
        # when the customer leaves each product page.
        durations = [v.duration_seconds for v in views if v.duration_seconds and v.duration_seconds > 0]
        avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0

        # Category diversity = number of different categories viewed.
        categories_seen = set()
        for pid in visited_ids:
            product = Product.query.get(pid)
            if product:
                categories_seen.add(product.category)

        # Purchase rate = purchases as a percentage of successful logins/sessions.
        purchase_rate = round((len(orders) / len(logins)) * 100, 2) if logins else 0.0

        devices = set(l.device_type for l in logins)
        if devices == {"Mobile"}:
            device_type = "Mobile"
        elif devices == {"Desktop"}:
            device_type = "Desktop"
        elif devices:
            device_type = "Mixed"
        else:
            device_type = "N/A"

        all_metrics.append({
            "customer_id": customer.customer_id,
            "name": customer.name,
            "login_frequency": len(logins),
            "avg_session_duration": avg_duration,
            "products_visited_count": len(visited_ids),
            "products_visited_ids": ";".join(visited_ids),
            "search_count": search_count,
            "added_to_cart": cart_add_count,
            "wishlist_count": wishlist_count,
            "cart_count": cart_count,
            "purchase_count": len(orders),
            "category_diversity": len(categories_seen),
            "purchase_rate": purchase_rate,
            "device_type": device_type,
        })

    return all_metrics


@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    metrics = build_customer_metrics()
    metrics.sort(key=lambda m: m["login_frequency"], reverse=True)

    total_customers = Customer.query.count()
    total_orders = Order.query.count()
    total_logins = LoginLog.query.count()
    total_searches = SearchLog.query.count()
    total_product_views = ProductView.query.count()
    total_cart_events = CartEvent.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    total_products = Product.query.count()

    top_searches = (db.session.query(SearchLog.search_query, db.func.count(SearchLog.id))
                     .group_by(SearchLog.search_query)
                     .order_by(db.func.count(SearchLog.id).desc()).limit(8).all())
    category_counts = (db.session.query(Product.category, db.func.count(OrderItem.id))
                        .join(OrderItem, OrderItem.product_id == Product.product_id)
                        .group_by(Product.category).all())

    top_bought_products = (db.session.query(
                                Product.name,
                                db.func.sum(OrderItem.quantity).label("units_bought"),
                                db.func.count(db.distinct(OrderItem.order_id)).label("order_count")
                            )
                            .join(OrderItem, OrderItem.product_id == Product.product_id)
                            .group_by(Product.product_id, Product.name)
                            .order_by(db.func.sum(OrderItem.quantity).desc())
                            .limit(10).all())

    return render_template("admin_dashboard.html", metrics=metrics,
                            total_customers=total_customers, total_orders=total_orders,
                            total_logins=total_logins, total_searches=total_searches,
                            total_product_views=total_product_views, total_cart_events=total_cart_events,
                            total_revenue=total_revenue, total_products=total_products,
                            top_searches=top_searches, category_counts=category_counts,
                            top_bought_products=top_bought_products)


@app.route("/admin/export/csv")
def admin_export_csv():
    if not session.get("admin_id"):
        return redirect(url_for("admin_login"))

    metrics = build_customer_metrics()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Customer_ID", "Login_Frequency", "Session_Duration", "Products_Visited_Count",
        "Products_Visited_ID", "Search_Count", "Add_To_Cart_Count", "Wishlist_Count",
        "Cart_Count", "Purchase_Count", "Category_Diversity", "Purchase_Rate",
    ])
    for m in metrics:
        writer.writerow([
            m["customer_id"], m["login_frequency"], m["avg_session_duration"],
            m["products_visited_count"], m["products_visited_ids"], m["search_count"],
            m["added_to_cart"], m["wishlist_count"], m["cart_count"], m["purchase_count"],
            m["category_diversity"], m["purchase_rate"],
        ])

    mem_file = io.BytesIO(output.getvalue().encode("utf-8"))
    filename = "behavioral_data_" + (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y%m%d_%H%M%S") + ".csv"
    return send_file(mem_file, mimetype="text/csv", as_attachment=True, download_name=filename)


# ---------------------------------------------------------------------------
# Start the app
# ---------------------------------------------------------------------------

def sync_product_catalog():
    # Keep product names simple and professional across existing databases.
    simple_names = {
        "Classic Water Bottle": "Water Bottle",
        "Daily Handbag": "Handbag",
        "College Backpack": "Backpack",
        "Spiral Notebook": "Notebook",
        "Blue Pen Pack": "Blue Pens",
        "Lunch Box": "Lunch Box",
        "Coffee Mug": "Coffee Mug",
        "Foldable Umbrella": "Umbrella",
        "Classic Sunglasses": "Sunglasses",
        "Slim Wallet": "Wallet",
        "Cotton Cap": "Cap",
        "Basic T-Shirt": "T-Shirt",
        "Desk Organizer": "Desk Organizer",
        "Wired Headphones": "Headphones",
        "Phone Stand": "Phone Stand",
        "Study Table Lamp": "Table Lamp",
        "Simple Wrist Watch": "Wrist Watch",
        "Cute Keychain": "Keychain",
        "Canvas Tote Bag": "Tote Bag",
        "Makeup Pouch": "Makeup Pouch",
    }
    changed = False
    for product in Product.query.all():
        if product.name in simple_names and product.name != simple_names[product.name]:
            product.name = simple_names[product.name]
            changed = True
    if changed:
        db.session.commit()

    """Keep an existing local database aligned with the current DH STORE catalog."""
    image_map = {
        "Classic Water Bottle": ("water-bottle.png", "Kitchen"),
        "Daily Handbag": ("handbag.png", "Bags"),
        "College Backpack": ("backpack.png", "Bags"),
        "Spiral Notebook": ("notebook.png", "Stationery"),
        "Blue Pen Pack": ("pens.png", "Stationery"),
        "Lunch Box": ("lunch-box.png", "Kitchen"),
        "Coffee Mug": ("mug.png", "Kitchen"),
        "Foldable Umbrella": ("umbrella.png", "Daily Use"),
        "Classic Sunglasses": ("sunglasses.png", "Fashion"),
        "Slim Wallet": ("wallet.png", "Accessories"),
        "Cotton Cap": ("cap.png", "Fashion"),
        "Basic T-Shirt": ("tshirt.png", "Fashion"),
        "Desk Organizer": ("desk-organizer.png", "Stationery"),
        "Wired Headphones": ("headphones.png", "Electronics"),
        "Phone Stand": ("phone-stand.png", "Electronics"),
        "Study Table Lamp": ("table-lamp.png", "Home"),
        "Simple Wrist Watch": ("watch.png", "Accessories"),
        "Cute Keychain": ("keychain.png", "Accessories"),
        "Canvas Tote Bag": ("tote-bag.png", "Bags"),
        "Makeup Pouch": ("makeup-pouch.png", "Accessories"),
    }
    # If an older copy still has the slippers product, convert it to the replacement product.
    old = Product.query.filter_by(name="Daily Slippers").first()
    if old:
        old.name = "Desk Organizer"
    changed = False
    for product in Product.query.all():
        if product.name in image_map:
            image_name, category = image_map[product.name]
            if product.image_seed != image_name:
                product.image_seed = image_name
                changed = True
            if product.category != category:
                product.category = category
                changed = True
    if old:
        changed = True
    if changed:
        db.session.commit()


def ensure_size_columns():
    """Add size columns to an existing SQLite database without deleting customer data."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)

    if "cart_items" in inspector.get_table_names():
        cart_columns = {col["name"] for col in inspector.get_columns("cart_items")}
        if "selected_size" not in cart_columns:
            db.session.execute(text("ALTER TABLE cart_items ADD COLUMN selected_size VARCHAR(20)"))

    if "order_items" in inspector.get_table_names():
        order_columns = {col["name"] for col in inspector.get_columns("order_items")}
        if "selected_size" not in order_columns:
            db.session.execute(text("ALTER TABLE order_items ADD COLUMN selected_size VARCHAR(20)"))

    db.session.commit()


def init_db():
    os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
    with app.app_context():
        db.create_all()
        ensure_size_columns()
        count = seed_products()
        seed_admin()
        sync_product_catalog()
        if count:
            print("Seeded " + str(count) + " products.")


init_db()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
