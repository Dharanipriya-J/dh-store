"""
Database models for the Behavioral Entropy E-Commerce DH STORE.

Every table that feeds the analytics dashboard / CSV export is annotated
below with the dataset column it maps to, so this stays in sync with the
Behavioral Entropy Analysis ML project this store was built to feed.
"""
import random
import string
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _gen_id(prefix, length=8):
    chars = string.ascii_uppercase + string.digits
    return prefix + "".join(random.choices(chars, k=length))


def generate_customer_id():
    """e.g. CU8X4P9A21 -> 'CU' + 8 random alphanumeric chars."""
    new_id = _gen_id("CU", 8)
    while Customer.query.get(new_id):
        new_id = _gen_id("CU", 8)
    return new_id


def generate_product_id():
    """e.g. PD3F7K2A -> 'PD' + 6 random alphanumeric chars."""
    new_id = _gen_id("PD", 6)
    while Product.query.get(new_id):
        new_id = _gen_id("PD", 6)
    return new_id


def generate_order_id():
    new_id = _gen_id("OD", 8)
    while Order.query.get(new_id):
        new_id = _gen_id("OD", 8)
    return new_id


class Customer(db.Model):
    __tablename__ = "customers"
    customer_id = db.Column(db.String(16), primary_key=True, default=generate_customer_id)
    name = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(15), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    addresses = db.relationship("Address", backref="customer", lazy=True, cascade="all, delete-orphan")
    cart_items = db.relationship("CartItem", backref="customer", lazy=True, cascade="all, delete-orphan")
    wishlist_items = db.relationship("WishlistItem", backref="customer", lazy=True, cascade="all, delete-orphan")
    orders = db.relationship("Order", backref="customer", lazy=True)


class Product(db.Model):
    __tablename__ = "products"
    product_id = db.Column(db.String(16), primary_key=True, default=generate_product_id)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    price = db.Column(db.Float, nullable=False)
    mrp = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    specification = db.Column(db.Text, nullable=False)  # newline separated key: value
    image_seed = db.Column(db.String(80), nullable=False)
    rating = db.Column(db.Float, default=4.0)
    stock = db.Column(db.Integer, default=50)

    def spec_dict(self):
        result = {}
        for line in (self.specification or "").split("\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                result[k.strip()] = v.strip()
        return result

    def image_url(self):
        return f"/static/img/{self.image_seed}"

    def purchase_options(self):
        """Options that must be selected before adding applicable products to cart."""
        options = {}
        if self.name == "Basic T-Shirt":
            options["Size"] = ["S", "M", "L", "XL", "XXL"]
        return options

    def requires_purchase_option(self):
        return bool(self.purchase_options())


class Address(db.Model):
    __tablename__ = "addresses"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(16), db.ForeignKey("customers.customer_id"), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    line1 = db.Column(db.String(200), nullable=False)
    line2 = db.Column(db.String(200))
    city = db.Column(db.String(80), nullable=False)
    state = db.Column(db.String(80), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    landmark = db.Column(db.String(150))


class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(16), db.ForeignKey("customers.customer_id"), nullable=False)
    product_id = db.Column(db.String(16), db.ForeignKey("products.product_id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    selected_size = db.Column(db.String(20), nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")


class WishlistItem(db.Model):
    __tablename__ = "wishlist_items"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(16), db.ForeignKey("customers.customer_id"), nullable=False)
    product_id = db.Column(db.String(16), db.ForeignKey("products.product_id"), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")


class Order(db.Model):
    __tablename__ = "orders"
    order_id = db.Column(db.String(16), primary_key=True, default=generate_order_id)
    customer_id = db.Column(db.String(16), db.ForeignKey("customers.customer_id"), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    line1 = db.Column(db.String(200), nullable=False)
    line2 = db.Column(db.String(200))
    city = db.Column(db.String(80), nullable=False)
    state = db.Column(db.String(80), nullable=False)
    pincode = db.Column(db.String(10), nullable=False)
    landmark = db.Column(db.String(150))
    payment_method = db.Column(db.String(20), default="COD")
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(30), default="Placed")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(16), db.ForeignKey("orders.order_id"), nullable=False)
    product_id = db.Column(db.String(16), db.ForeignKey("products.product_id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price = db.Column(db.Float, nullable=False)
    selected_size = db.Column(db.String(20), nullable=True)

    product = db.relationship("Product")


# ---------------------------------------------------------------------------
# Behavioral tracking tables -> feed the admin dashboard + CSV export, which
# in turn feeds the Behavioral Entropy Analysis ML pipeline.
# ---------------------------------------------------------------------------

class LoginLog(db.Model):
    """One row per successful login -> Login_Frequency."""
    __tablename__ = "login_logs"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(16), db.ForeignKey("customers.customer_id"), nullable=False)
    device_type = db.Column(db.String(20), default="Desktop")  # Mobile / Desktop
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class ProductView(db.Model):
    """One row per product page visit -> Products_Visited, Session_Duration."""
    __tablename__ = "product_views"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(16), db.ForeignKey("customers.customer_id"), nullable=False)
    product_id = db.Column(db.String(16), db.ForeignKey("products.product_id"), nullable=False)
    duration_seconds = db.Column(db.Float, default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class SearchLog(db.Model):
    """One row per search query -> Search_Count."""
    __tablename__ = "search_logs"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(16), db.ForeignKey("customers.customer_id"), nullable=False)
    search_query = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class CartEvent(db.Model):
    """One row per 'add to cart' click -> Added_To_Cart (event count, not live cart size)."""
    __tablename__ = "cart_events"
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(16), db.ForeignKey("customers.customer_id"), nullable=False)
    product_id = db.Column(db.String(16), db.ForeignKey("products.product_id"), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Admin(db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
