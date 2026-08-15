from datetime import datetime
from app import db

class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    gateway = db.Column(db.String(50), default='razorpay') # razorpay, cash_on_delivery
    transaction_id = db.Column(db.String(100), nullable=True)
    gateway_order_id = db.Column(db.String(100), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    status = db.Column(db.String(20), default='PENDING') # PENDING, SUCCESS, FAILED, REFUNDED
    payment_method = db.Column(db.String(50), nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
