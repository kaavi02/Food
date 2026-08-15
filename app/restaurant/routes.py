from flask import render_template, redirect, url_for, flash, request, current_app, abort, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import db
from app.restaurant import restaurant
from app.restaurant.forms import RestaurantForm, CategoryForm, FoodItemForm
from app.models import Restaurant, FoodCategory, FoodItem, Order, OrderItem, OrderStatusHistory
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
    recent_orders = Order.query.options(
        joinedload(Order.customer),
        joinedload(Order.items).joinedload(OrderItem.food_item)
    ).filter_by(restaurant_id=resto.id).order_by(Order.created_at.desc()).limit(10).all()
    
    total_sales = sum(
        o.total_amount for o in Order.query.filter_by(restaurant_id=resto.id, order_status='DELIVERED').all()
    )
    total_orders = Order.query.filter_by(restaurant_id=resto.id).count()
    
    return render_template(
        'restaurant/dashboard.html',
        restaurant=resto,
        recent_orders=recent_orders,
        total_sales=total_sales,
        total_orders=total_orders
    )

@restaurant.route('/orders')
@login_required
@role_required('restaurant_owner')
def orders():
    resto = Restaurant.query.filter_by(owner_id=current_user.id).first()
    if not resto:
        return redirect(url_for('restaurant.setup_restaurant'))
        
    all_orders = Order.query.options(
        joinedload(Order.customer),
        joinedload(Order.address),
        joinedload(Order.items).joinedload(OrderItem.food_item)
    ).filter_by(restaurant_id=resto.id).order_by(Order.created_at.desc()).all()
    
    return render_template('restaurant/dashboard.html', restaurant=resto, recent_orders=all_orders)

@restaurant.route('/order/<int:order_id>/status', methods=['POST'])
@login_required
@role_required('restaurant_owner')
def update_order_status(order_id):
    resto = Restaurant.query.filter_by(owner_id=current_user.id).first_or_404()
    order = Order.query.filter_by(id=order_id, restaurant_id=resto.id).first_or_404()
    
    new_status = request.form.get('status')
    valid_statuses = ['CONFIRMED', 'PREPARING', 'READY_FOR_PICKUP', 'CANCELLED']
    if new_status in valid_statuses:
        order.order_status = new_status
        history = OrderStatusHistory(
            order_id=order.id,
            status=new_status,
            changed_by=current_user.id,
            message=f'Order {new_status.lower().replace("_", " ")} by kitchen'
        )
        db.session.add(history)
        db.session.commit()
        flash(f'Order #{order.order_number} marked as {new_status}.', 'success')
    else:
        flash('Invalid status provided.', 'danger')
        
    return redirect(request.referrer or url_for('restaurant.dashboard'))

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
    categories = FoodCategory.query.options(
        joinedload(FoodCategory.food_items)
    ).filter_by(restaurant_id=resto.id).order_by(FoodCategory.display_order).all()
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

@restaurant.route('/food/<int:food_id>/toggle', methods=['POST'])
@login_required
@role_required('restaurant_owner')
def toggle_food(food_id):
    resto = Restaurant.query.filter_by(owner_id=current_user.id).first_or_404()
    food = FoodItem.query.filter_by(id=food_id, restaurant_id=resto.id).first_or_404()
    food.is_available = not food.is_available
    db.session.commit()
    status_str = 'available' if food.is_available else 'out of stock'
    flash(f'{food.name} is now {status_str}.', 'success')
    return redirect(url_for('restaurant.menu'))

@restaurant.route('/food/<int:food_id>/delete', methods=['POST'])
@login_required
@role_required('restaurant_owner')
def delete_food(food_id):
    resto = Restaurant.query.filter_by(owner_id=current_user.id).first_or_404()
    food = FoodItem.query.filter_by(id=food_id, restaurant_id=resto.id).first_or_404()
    db.session.delete(food)
    db.session.commit()
    flash(f'{food.name} deleted from menu.', 'info')
    return redirect(url_for('restaurant.menu'))
