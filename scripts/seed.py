import os
import sys
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db, bcrypt
from app.models import User, Restaurant, FoodCategory, FoodItem

def download_image(url, filename):
    app = create_app()
    upload_folder = app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    
    if not os.path.exists(filepath):
        try:
            print(f"Downloading {filename}...")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(filepath, 'wb') as out_file:
                out_file.write(response.read())
        except Exception as e:
            print(f"Failed to download {filename}: {e}")
    return filename

def seed_database():
    app = create_app()
    with app.app_context():
        print("Clearing existing data...")
        db.drop_all()
        db.create_all()
        
        print("Creating users...")
        admin = User(
            first_name="Admin", last_name="User", email="admin@food.com",
            password_hash=bcrypt.generate_password_hash("password").decode('utf-8'),
            role="admin"
        )
        owner1 = User(
            first_name="Spice", last_name="Owner", email="spice@food.com",
            password_hash=bcrypt.generate_password_hash("password").decode('utf-8'),
            role="restaurant_owner"
        )
        owner2 = User(
            first_name="Burger", last_name="Owner", email="burger@food.com",
            password_hash=bcrypt.generate_password_hash("password").decode('utf-8'),
            role="restaurant_owner"
        )
        owner3 = User(
            first_name="Pizza", last_name="Owner", email="pizza@food.com",
            password_hash=bcrypt.generate_password_hash("password").decode('utf-8'),
            role="restaurant_owner"
        )
        delivery = User(
            first_name="Fast", last_name="Delivery", email="delivery@food.com",
            password_hash=bcrypt.generate_password_hash("password").decode('utf-8'),
            role="delivery_partner"
        )
        customer = User(
            first_name="John", last_name="Doe", email="customer@food.com",
            password_hash=bcrypt.generate_password_hash("password").decode('utf-8'),
            role="customer", phone="1234567890"
        )
        db.session.add_all([admin, owner1, owner2, owner3, delivery, customer])
        db.session.commit()
        
        # Images for restaurants
        print("Setting up restaurants with images...")
        img_rest1 = download_image("https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80", "rest1.jpg")
        img_rest2 = download_image("https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800&q=80", "rest2.jpg")
        img_rest3 = download_image("https://images.unsplash.com/photo-1579684947550-22e945225d9a?w=800&q=80", "rest3.jpg")
        
        rest1 = Restaurant(owner_id=owner1.id, name="Spice Garden", description="Authentic Indian cuisine with rich flavors.", address="123 Curry Lane", city="Foodville", phone="555-0101", cuisine_type="Indian", rating=4.8, delivery_fee=40.0, minimum_order=150.0, is_active=True, image=img_rest1)
        rest2 = Restaurant(owner_id=owner2.id, name="Burger House", description="Juicy burgers and crispy fries.", address="456 Grill Blvd", city="Foodville", phone="555-0102", cuisine_type="American", rating=4.5, delivery_fee=30.0, minimum_order=100.0, is_active=True, image=img_rest2)
        rest3 = Restaurant(owner_id=owner3.id, name="Pizza Corner", description="Wood-fired oven pizzas.", address="789 Slice Ave", city="Foodville", phone="555-0103", cuisine_type="Italian", rating=4.7, delivery_fee=45.0, minimum_order=200.0, is_active=True, image=img_rest3)
        
        db.session.add_all([rest1, rest2, rest3])
        db.session.commit()
        
        print("Setting up categories and food items with images...")
        # Rest 1 (Spice Garden)
        cat_curry = FoodCategory(restaurant_id=rest1.id, name="Curries", description="Rich and spicy gravies")
        cat_bread = FoodCategory(restaurant_id=rest1.id, name="Breads", description="Freshly baked flatbreads")
        db.session.add_all([cat_curry, cat_bread])
        db.session.commit()
        
        img_butter_chicken = download_image("https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?w=800&q=80", "butter_chicken.jpg")
        img_palak_paneer = download_image("https://images.unsplash.com/photo-1626776876729-bab4369a5a5a?w=800&q=80", "palak_paneer.jpg")
        img_naan = download_image("https://images.unsplash.com/photo-1626074353765-517a681e40be?w=800&q=80", "garlic_naan.jpg")
        
        db.session.add_all([
            FoodItem(restaurant_id=rest1.id, category_id=cat_curry.id, name="Butter Chicken", description="Tender chicken in creamy tomato sauce", price=280.0, is_available=True, image=img_butter_chicken),
            FoodItem(restaurant_id=rest1.id, category_id=cat_curry.id, name="Palak Paneer", description="Cottage cheese in spinach gravy", price=220.0, is_vegetarian=True, is_available=True, image=img_palak_paneer),
            FoodItem(restaurant_id=rest1.id, category_id=cat_bread.id, name="Garlic Naan", description="Soft bread with garlic and butter", price=50.0, is_vegetarian=True, is_available=True, image=img_naan)
        ])
        
        # Rest 2 (Burger House)
        cat_burger = FoodCategory(restaurant_id=rest2.id, name="Burgers", description="Hand-crafted burgers")
        db.session.add(cat_burger)
        db.session.commit()
        
        img_classic = download_image("https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800&q=80", "classic_burger.jpg")
        img_veggie = download_image("https://images.unsplash.com/photo-1520072959219-c595dc870360?w=800&q=80", "veggie_burger.jpg")
        
        db.session.add_all([
            FoodItem(restaurant_id=rest2.id, category_id=cat_burger.id, name="Classic Cheeseburger", description="Beef patty with cheddar", price=180.0, is_available=True, image=img_classic),
            FoodItem(restaurant_id=rest2.id, category_id=cat_burger.id, name="Veggie Burger", description="Plant-based patty", price=140.0, is_vegetarian=True, is_vegan=True, is_available=True, image=img_veggie)
        ])
        
        # Rest 3 (Pizza Corner)
        cat_pizza = FoodCategory(restaurant_id=rest3.id, name="Wood-fired Pizzas", description="Authentic Neapolitan Pizzas")
        db.session.add(cat_pizza)
        db.session.commit()
        
        img_margherita = download_image("https://images.unsplash.com/photo-1574071318508-1cdbab80d002?w=800&q=80", "margherita.jpg")
        img_pepperoni = download_image("https://images.unsplash.com/photo-1628840042765-356cda07504e?w=800&q=80", "pepperoni.jpg")
        
        db.session.add_all([
            FoodItem(restaurant_id=rest3.id, category_id=cat_pizza.id, name="Margherita", description="Classic tomato, basil, and mozzarella", price=299.0, is_vegetarian=True, is_available=True, image=img_margherita),
            FoodItem(restaurant_id=rest3.id, category_id=cat_pizza.id, name="Pepperoni", description="Spicy pepperoni and cheese", price=399.0, is_available=True, image=img_pepperoni)
        ])
        
        db.session.commit()
        print("Database seeded successfully with realistic prices!")

if __name__ == "__main__":
    seed_database()
