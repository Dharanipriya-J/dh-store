# DH STORE product and admin seed data

import os

from werkzeug.security import generate_password_hash

from models import db, Product, Admin, generate_product_id


CATALOG = [
    (
        "Water Bottle",
        "Kitchen",
        299,
        399,
        "water-bottle.png",
        "Simple 1 litre reusable water bottle.",
        "Capacity: 1L\nMaterial: Metal\nColour: Black",
    ),
    (
        "Handbag",
        "Bags",
        699,
        899,
        "handbag.png",
        "Simple handbag for everyday use.",
        "Material: Synthetic Leather\nSize: Medium\nColour: Brown",
    ),
    (
        "Backpack",
        "Bags",
        899,
        1199,
        "backpack.png",
        "Useful backpack for college and daily travel.",
        "Material: Polyester\nCapacity: 20L\nColour: Blue",
    ),
    (
        "Notebook",
        "Stationery",
        149,
        199,
        "notebook.png",
        "A simple ruled notebook for notes and writing.",
        "Pages: 160\nType: Ruled\nSize: A5",
    ),
    (
        "Blue Pens",
        "Stationery",
        99,
        129,
        "pens.png",
        "Pack of smooth blue ball pens.",
        "Pack: 5 Pens\nInk: Blue\nType: Ball Pen",
    ),
    (
        "Lunch Box",
        "Kitchen",
        399,
        499,
        "lunch-box.png",
        "Compact lunch box for school, college or office.",
        "Material: Plastic\nCompartments: 3\nCapacity: 800ml",
    ),
    (
        "Coffee Mug",
        "Kitchen",
        199,
        299,
        "mug.png",
        "Simple coffee mug for tea or coffee.",
        "Material: Ceramic\nCapacity: 300ml\nColour: Brown",
    ),
    (
        "Umbrella",
        "Daily Use",
        449,
        599,
        "umbrella.png",
        "Small umbrella that is easy to carry.",
        "Type: Foldable\nFrame: Metal\nSize: 21 inch",
    ),
    (
        "Sunglasses",
        "Fashion",
        349,
        499,
        "sunglasses.png",
        "Simple sunglasses for everyday outdoor use.",
        "Frame: Plastic\nLens: UV Protected\nStyle: Classic",
    ),
    (
        "Wallet",
        "Accessories",
        299,
        399,
        "wallet.png",
        "Small wallet with useful card slots.",
        "Material: Leather\nSlots: 6\nColour: Brown",
    ),
    (
        "Cap",
        "Fashion",
        199,
        299,
        "cap.png",
        "Comfortable cotton cap for casual wear.",
        "Material: Cotton\nSize: Adjustable\nColour: Black",
    ),
    (
        "T-Shirt",
        "Fashion",
        499,
        699,
        "tshirt.png",
        "Simple round-neck cotton T-shirt.",
        "Material: Cotton\nFit: Regular\nSize: S-XXL",
    ),
    (
        "Desk Organizer",
        "Stationery",
        249,
        349,
        "desk-organizer.png",
        "Simple organizer for pens and small desk items.",
        "Material: Plastic\nCompartments: 4\nColour: Black",
    ),
    (
        "Headphones",
        "Electronics",
        599,
        799,
        "headphones.png",
        "Simple wired headphones for music and calls.",
        "Connection: 3.5mm\nMicrophone: Yes\nCable: 1.2m",
    ),
    (
        "Phone Stand",
        "Electronics",
        249,
        349,
        "phone-stand.png",
        "Small stand for keeping your phone on a desk.",
        "Material: Plastic\nType: Foldable\nUse: Mobile",
    ),
    (
        "Table Lamp",
        "Home",
        499,
        699,
        "table-lamp.png",
        "Basic LED table lamp for study time.",
        "Light: LED\nPower: 5W\nSwitch: On/Off",
    ),
    (
        "Wrist Watch",
        "Accessories",
        799,
        999,
        "watch.png",
        "Classic watch with a simple dial.",
        "Movement: Quartz\nStrap: Leatherette\nDial: Analog",
    ),
    (
        "Keychain",
        "Accessories",
        99,
        149,
        "keychain.png",
        "Small keychain for bags and keys.",
        "Material: Metal\nType: Key Ring\nSize: Small",
    ),
    (
        "Tote Bag",
        "Bags",
        349,
        499,
        "tote-bag.png",
        "Reusable tote bag for shopping and daily use.",
        "Material: Canvas\nCapacity: 8kg\nColour: Printed",
    ),
    (
        "Makeup Pouch",
        "Accessories",
        249,
        349,
        "makeup-pouch.png",
        "Small pouch for cosmetics and personal items.",
        "Material: Fabric\nClosure: Zip\nSize: Small",
    ),
]


def seed_products():
    """Add the default products if the database is empty."""

    if Product.query.first():
        return 0

    count = 0

    for name, category, price, mrp, image_seed, desc, specs in CATALOG:
        product = Product(
            product_id=generate_product_id(),
            name=name,
            category=category,
            price=price,
            mrp=mrp,
            description=desc,
            specification=specs,
            image_seed=image_seed,
            rating=round(4.0 + (count % 10) / 10, 1),
            stock=30 + (count % 40),
        )

        db.session.add(product)
        count += 1

    db.session.commit()

    return count


def seed_admin():
    """Create the default admin using ADMIN_PASSWORD from the environment."""

    admin = Admin.query.first()

    if admin:
        return 0

    admin_password = os.environ.get("ADMIN_PASSWORD")

    if not admin_password:
        raise RuntimeError(
            "ADMIN_PASSWORD environment variable is not set."
        )

    admin = Admin(
        username="dh@admin",
        password_hash=generate_password_hash(admin_password),
    )

    db.session.add(admin)
    db.session.commit()

    return 1