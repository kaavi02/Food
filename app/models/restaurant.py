from datetime import datetime
from app import db

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    cuisine_type = db.Column(db.String(100), nullable=True)
    rating = db.Column(db.Float, default=0.0)
    delivery_fee = db.Column(db.Float, default=0.0)
    minimum_order = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    operating_hours = db.relationship('RestaurantOperatingHours', backref='restaurant', lazy=True, cascade="all, delete-orphan")
    categories = db.relationship('FoodCategory', backref='restaurant', lazy=True, cascade="all, delete-orphan")
    food_items = db.relationship('FoodItem', backref='restaurant', lazy=True, cascade="all, delete-orphan")
    orders = db.relationship('Order', backref='restaurant', lazy=True)
    reviews = db.relationship('Review', backref='restaurant', lazy=True)

class RestaurantOperatingHours(db.Model):
    __tablename__ = 'restaurant_operating_hours'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    day_of_week = db.Column(db.String(10), nullable=False) # Monday, Tuesday, etc.
    opening_time = db.Column(db.Time, nullable=True)
    closing_time = db.Column(db.Time, nullable=True)
    is_closed = db.Column(db.Boolean, default=False)
