from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.restaurant import restaurant
from app.restaurant.forms import RestaurantForm, CategoryForm, FoodItemForm
from app.models import Restaurant, FoodCategory, FoodItem, Order
from app.utils.decorators import role_required
import os
import secrets
from werkzeug.utils import secure_filename

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
    form_picture.save(picture_path)
    return picture_fn

@restaurant.route('/dashboard')
@login_required
@role_required('restaurant_owner')
def dashboard():
    resto = Restaurant.query.filter_by(owner_id=current_user.id).first()
    if not resto:
        return redirect(url_for('restaurant.setup_restaurant'))
    
    # Get recent orders
    recent_orders = Order.query.filter_by(restaurant_id=resto.id).order_by(Order.created_at.desc()).limit(5).all()
    return render_template('restaurant/dashboard.html', restaurant=resto, recent_orders=recent_orders)

@restaurant.route('/setup', methods=['GET', 'POST'])
@login_required
@role_required('restaurant_owner')
def setup_restaurant():
    resto = Restaurant.query.filter_by(owner_id=current_user.id).first()
    form = RestaurantForm()
    
    if form.validate_on_submit():
        if not resto:
            resto = Restaurant(owner_id=current_user.id)
            db.session.add(resto)
        
        resto.name = form.name.data
        resto.description = form.description.data
        resto.address = form.address.data
        resto.city = form.city.data
        resto.phone = form.phone.data
        resto.email = form.email.data
        resto.cuisine_type = form.cuisine_type.data
        resto.delivery_fee = form.delivery_fee.data
        resto.minimum_order = form.minimum_order.data
        resto.is_active = form.is_active.data
        
        if form.image.data:
            picture_file = save_picture(form.image.data)
            resto.image = picture_file
            
        db.session.commit()
        flash('Restaurant settings saved!', 'success')
        return redirect(url_for('restaurant.dashboard'))
    
    elif request.method == 'GET' and resto:
        form.name.data = resto.name
        form.description.data = resto.description
        form.address.data = resto.address
        form.city.data = resto.city
        form.phone.data = resto.phone
        form.email.data = resto.email
        form.cuisine_type.data = resto.cuisine_type
        form.delivery_fee.data = resto.delivery_fee
        form.minimum_order.data = resto.minimum_order
        form.is_active.data = resto.is_active
        
    return render_template('restaurant/setup.html', title='Restaurant Setup', form=form)

@restaurant.route('/menu', methods=['GET'])
@login_required
@role_required('restaurant_owner')
def menu():
    resto = Restaurant.query.filter_by(owner_id=current_user.id).first()
    if not resto:
        return redirect(url_for('restaurant.setup_restaurant'))
    categories = FoodCategory.query.filter_by(restaurant_id=resto.id).order_by(FoodCategory.display_order).all()
    return render_template('restaurant/menu.html', categories=categories, restaurant=resto)

@restaurant.route('/category/add', methods=['GET', 'POST'])
@login_required
@role_required('restaurant_owner')
def add_category():
    resto = Restaurant.query.filter_by(owner_id=current_user.id).first_or_404()
    form = CategoryForm()
    if form.validate_on_submit():
        category = FoodCategory(
            restaurant_id=resto.id,
            name=form.name.data,
            description=form.description.data,
            display_order=form.display_order.data,
            is_active=form.is_active.data
        )
        db.session.add(category)
        db.session.commit()
        flash('Category added!', 'success')
        return redirect(url_for('restaurant.menu'))
    return render_template('restaurant/category_form.html', form=form, title="Add Category")

@restaurant.route('/category/<int:category_id>/food/add', methods=['GET', 'POST'])
@login_required
@role_required('restaurant_owner')
def add_food(category_id):
    resto = Restaurant.query.filter_by(owner_id=current_user.id).first_or_404()
    category = FoodCategory.query.get_or_404(category_id)
    if category.restaurant_id != resto.id:
        abort(403)
        
    form = FoodItemForm()
    if form.validate_on_submit():
        food = FoodItem(
            restaurant_id=resto.id,
            category_id=category.id,
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            preparation_time=form.preparation_time.data,
            is_vegetarian=form.is_vegetarian.data,
            is_vegan=form.is_vegan.data,
            is_available=form.is_available.data
        )
        if form.image.data:
            food.image = save_picture(form.image.data)
        db.session.add(food)
        db.session.commit()
        flash('Food item added!', 'success')
        return redirect(url_for('restaurant.menu'))
    return render_template('restaurant/food_form.html', form=form, title="Add Food Item", category=category)
