from datetime import datetime
from app import db
import string
import random

def generate_order_number():
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return f"ORD-{date_str}-{random_str}"

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False, default=generate_order_number)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    delivery_partner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    address_id = db.Column(db.Integer, db.ForeignKey('addresses.id'), nullable=False)
    
    subtotal = db.Column(db.Float, nullable=False)
    delivery_fee = db.Column(db.Float, nullable=False)
    tax = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    
    payment_status = db.Column(db.String(20), default='PENDING') # PENDING, SUCCESS, FAILED, REFUNDED
    order_status = db.Column(db.String(20), default='PLACED') # PLACED, CONFIRMED, PREPARING, READY_FOR_PICKUP, OUT_FOR_DELIVERY, DELIVERED, CANCELLED, REJECTED
    special_instructions = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    estimated_delivery_time = db.Column(db.DateTime, nullable=True)

    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    status_history = db.relationship('OrderStatusHistory', backref='order', lazy=True, cascade="all, delete-orphan")
    payment = db.relationship('Payment', backref='order', uselist=False)
    address = db.relationship('Address', backref='orders', lazy=True)

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    food_item_id = db.Column(db.Integer, db.ForeignKey('food_items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False) # price at the time of order
    
    food_item = db.relationship('FoodItem')

class OrderStatusHistory(db.Model):
    __tablename__ = 'order_status_history'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # user who changed it
    message = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
