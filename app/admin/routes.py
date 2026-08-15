from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc, case
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from app import db
from app.admin import admin
from app.models import (
    User, Address, Restaurant, FoodCategory, FoodItem,
    Order, OrderItem, OrderStatusHistory, Payment
)
from app.utils.decorators import role_required

@admin.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    # 1. Total counts in single queries
    total_users = User.query.count()
    total_restaurants = Restaurant.query.count()
    active_restaurants = Restaurant.query.filter_by(is_active=True).count()
    total_orders = Order.query.count()
    total_foods = FoodItem.query.count()
    
    # 2. Revenue & Status counts in a single query
    status_counts_query = db.session.query(
        Order.order_status,
        func.count(Order.id),
        func.sum(Order.total_amount)
    ).group_by(Order.order_status).all()
    
    status_counts = {
        'PLACED': 0, 'CONFIRMED': 0, 'PREPARING': 0,
        'READY_FOR_PICKUP': 0, 'OUT_FOR_DELIVERY': 0,
        'DELIVERED': 0, 'CANCELLED': 0
    }
    total_revenue = 0.0
    active_orders_count = 0
    
    for s, cnt, rev in status_counts_query:
        if s in status_counts:
            status_counts[s] = cnt
        if s == 'DELIVERED' and rev:
            total_revenue = float(rev)
        if s in ['PLACED', 'CONFIRMED', 'PREPARING', 'READY_FOR_PICKUP', 'OUT_FOR_DELIVERY']:
            active_orders_count += cnt

    # 3. User roles breakdown in single query
    user_roles_query = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
    users_by_role = {'customer': 0, 'restaurant_owner': 0, 'delivery_partner': 0, 'admin': 0}
    for r, cnt in user_roles_query:
        if r in users_by_role:
            users_by_role[r] = cnt

    # 4. Revenue by past 7 days (SINGLE query instead of 14 separate queries)
    today = datetime.utcnow().date()
    past_week = today - timedelta(days=6)
    start_dt = datetime.combine(past_week, datetime.min.time())
    
    recent_week_orders = Order.query.filter(Order.created_at >= start_dt).all()
    
    # Bucket orders by date in memory
    days = []
    daily_revenue = []
    daily_orders = []
    
    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        day_str = day_date.strftime('%b %d')
        days.append(day_str)
        
        day_orders = [o for o in recent_week_orders if o.created_at.date() == day_date]
        day_delivered = [o for o in day_orders if o.order_status == 'DELIVERED']
        
        daily_revenue.append(round(sum(o.total_amount for o in day_delivered), 2))
        daily_orders.append(len(day_orders))

    # 5. Top 5 Hotels by order count
    top_restaurants_query = db.session.query(
        Restaurant.name,
        func.count(Order.id).label('order_count')
    ).outerjoin(Order, Restaurant.id == Order.restaurant_id)\
     .group_by(Restaurant.id)\
     .order_by(desc('order_count'))\
     .limit(5).all()

    top_hotels_labels = [r[0] for r in top_restaurants_query]
    top_hotels_orders = [r[1] for r in top_restaurants_query]

    # 6. Recent 8 Orders (eager loaded in 1 query)
    recent_orders = Order.query.options(
        joinedload(Order.customer),
        joinedload(Order.restaurant)
    ).order_by(Order.created_at.desc()).limit(8).all()
    
    # 7. Recent 5 Users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_restaurants=total_restaurants,
        active_restaurants=active_restaurants,
        total_orders=total_orders,
        revenue=total_revenue,
        active_orders_count=active_orders_count,
        total_foods=total_foods,
        users_by_role=users_by_role,
        status_counts=status_counts,
        days=days,
        daily_revenue=daily_revenue,
        daily_orders=daily_orders,
        top_hotels_labels=top_hotels_labels,
        top_hotels_orders=top_hotels_orders,
        recent_orders=recent_orders,
        recent_users=recent_users
    )

@admin.route('/orders')
@login_required
@role_required('admin')
def orders():
    status_filter = request.args.get('status', 'all').upper()
    search_query = request.args.get('q', '').strip()
    
    # Eager load relationships to prevent N+1 queries
    query = Order.query.options(
        joinedload(Order.customer),
        joinedload(Order.restaurant),
        joinedload(Order.payment),
        joinedload(Order.items).joinedload(OrderItem.food_item)
    )
    
    if status_filter != 'ALL':
        query = query.filter(Order.order_status == status_filter)
        
    if search_query:
        query = query.join(User, Order.customer_id == User.id)\
                     .join(Restaurant, Order.restaurant_id == Restaurant.id)\
                     .filter(
                         (Order.order_number.ilike(f'%{search_query}%')) |
                         (User.first_name.ilike(f'%{search_query}%')) |
                         (User.last_name.ilike(f'%{search_query}%')) |
                         (Restaurant.name.ilike(f'%{search_query}%'))
                     )
        
    all_orders = query.order_by(Order.created_at.desc()).all()
    
    # Counts in a single grouped query
    status_counts_query = db.session.query(Order.order_status, func.count(Order.id)).group_by(Order.order_status).all()
    status_counts = {
        'ALL': 0, 'PLACED': 0, 'CONFIRMED': 0, 'PREPARING': 0,
        'READY_FOR_PICKUP': 0, 'OUT_FOR_DELIVERY': 0, 'DELIVERED': 0, 'CANCELLED': 0
    }
    total_cnt = 0
    for s, cnt in status_counts_query:
        if s in status_counts:
            status_counts[s] = cnt
        total_cnt += cnt
    status_counts['ALL'] = total_cnt
    
    return render_template(
        'admin/orders.html',
        orders=all_orders,
        status_filter=status_filter,
        search_query=search_query,
        status_counts=status_counts
    )

@admin.route('/orders/<int:order_id>')
@login_required
@role_required('admin')
def order_detail(order_id):
    order = Order.query.options(
        joinedload(Order.customer),
        joinedload(Order.restaurant),
        joinedload(Order.address),
        joinedload(Order.payment),
        joinedload(Order.items).joinedload(OrderItem.food_item)
    ).filter_by(id=order_id).first_or_404()
    
    history = OrderStatusHistory.query.filter_by(order_id=order_id).order_by(OrderStatusHistory.created_at.asc()).all()
    return render_template('admin/order_detail.html', order=order, history=history)

@admin.route('/orders/<int:order_id>/update_status', methods=['POST'])
@login_required
@role_required('admin')
def update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    note = request.form.get('note', f'Status updated to {new_status} by Admin')
    
    valid_statuses = ['PLACED', 'CONFIRMED', 'PREPARING', 'READY_FOR_PICKUP', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED']
    if new_status in valid_statuses:
        order.order_status = new_status
        if new_status == 'DELIVERED' and order.payment and order.payment.gateway == 'cod':
            order.payment.status = 'SUCCESS'
            order.payment_status = 'SUCCESS'
            order.payment.paid_at = datetime.utcnow()
            
        history = OrderStatusHistory(
            order_id=order.id,
            status=new_status,
            changed_by=current_user.id,
            message=note
        )
        db.session.add(history)
        db.session.commit()
        flash(f'Order #{order.order_number} status updated to {new_status}.', 'success')
    else:
        flash('Invalid status provided.', 'danger')
        
    return redirect(request.referrer or url_for('admin.orders'))

@admin.route('/restaurants')
@login_required
@role_required('admin')
def restaurants():
    search_query = request.args.get('q', '').strip()
    status_filter = request.args.get('status', 'all')
    
    query = Restaurant.query.options(joinedload(Restaurant.owner))
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
        
    if search_query:
        query = query.filter(
            (Restaurant.name.ilike(f'%{search_query}%')) |
            (Restaurant.cuisine_type.ilike(f'%{search_query}%')) |
            (Restaurant.city.ilike(f'%{search_query}%'))
        )
        
    all_restaurants = query.all()
    
    # Compute aggregated stats with valid case syntax
    orders_stats = db.session.query(
        Order.restaurant_id,
        func.count(Order.id),
        func.sum(case((Order.order_status == 'DELIVERED', Order.total_amount), else_=0.0))
    ).group_by(Order.restaurant_id).all()
    orders_map = {r[0]: (r[1], float(r[2] or 0)) for r in orders_stats}
    
    menu_stats = db.session.query(
        FoodItem.restaurant_id,
        func.count(FoodItem.id)
    ).group_by(FoodItem.restaurant_id).all()
    menu_map = {r[0]: r[1] for r in menu_stats}
    
    for r in all_restaurants:
        r.orders_count = orders_map.get(r.id, (0, 0))[0]
        r.total_sales = orders_map.get(r.id, (0, 0))[1]
        r.menu_items_count = menu_map.get(r.id, 0)
        
    active_count = sum(1 for r in all_restaurants if r.is_active)
    total_count = len(all_restaurants)
    
    return render_template(
        'admin/restaurants.html',
        restaurants=all_restaurants,
        search_query=search_query,
        status_filter=status_filter,
        total_count=total_count,
        active_count=active_count,
        inactive_count=total_count - active_count
    )

@admin.route('/restaurants/<int:restaurant_id>')
@login_required
@role_required('admin')
def restaurant_detail(restaurant_id):
    resto = Restaurant.query.options(joinedload(Restaurant.owner)).filter_by(id=restaurant_id).first_or_404()
    
    categories = FoodCategory.query.options(
        joinedload(FoodCategory.food_items)
    ).filter_by(restaurant_id=resto.id).order_by(FoodCategory.display_order).all()
    
    orders = Order.query.options(
        joinedload(Order.customer)
    ).filter_by(restaurant_id=resto.id).order_by(Order.created_at.desc()).limit(15).all()
    
    stats = db.session.query(
        func.count(Order.id),
        func.sum(case((Order.order_status == 'DELIVERED', Order.total_amount), else_=0.0))
    ).filter(Order.restaurant_id == resto.id).first()
    
    total_orders = stats[0] or 0
    total_sales = float(stats[1] or 0)
    
    return render_template(
        'admin/restaurant_detail.html',
        restaurant=resto,
        categories=categories,
        orders=orders,
        total_sales=total_sales,
        total_orders=total_orders
    )

@admin.route('/toggle_restaurant/<int:restaurant_id>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    restaurant.is_active = not restaurant.is_active
    db.session.commit()
    status_text = 'activated' if restaurant.is_active else 'deactivated'
    flash(f'Hotel "{restaurant.name}" has been {status_text}.', 'success')
    return redirect(request.referrer or url_for('admin.restaurants'))

@admin.route('/users')
@login_required
@role_required('admin')
def users():
    role_filter = request.args.get('role', 'all')
    search_query = request.args.get('q', '').strip()
    
    query = User.query
    if role_filter != 'all':
        query = query.filter_by(role=role_filter)
        
    if search_query:
        query = query.filter(
            (User.first_name.ilike(f'%{search_query}%')) |
            (User.last_name.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%')) |
            (User.phone.ilike(f'%{search_query}%'))
        )
        
    all_users = query.order_by(User.created_at.desc()).all()
    
    # User stats in 1 query
    roles_query = db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
    role_counts = {'all': 0, 'customer': 0, 'restaurant_owner': 0, 'delivery_partner': 0, 'admin': 0}
    total_u = 0
    for r, cnt in roles_query:
        if r in role_counts:
            role_counts[r] = cnt
        total_u += cnt
    role_counts['all'] = total_u
    
    return render_template(
        'admin/users.html',
        users=all_users,
        role_filter=role_filter,
        search_query=search_query,
        role_counts=role_counts
    )

@admin.route('/toggle_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own admin account.', 'warning')
    else:
        user.is_active = not user.is_active
        db.session.commit()
        status_text = 'activated' if user.is_active else 'deactivated'
        flash(f'User {user.email} has been {status_text}.', 'success')
    return redirect(request.referrer or url_for('admin.users'))

@admin.route('/users/<int:user_id>/change_role', methods=['POST'])
@login_required
@role_required('admin')
def change_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role')
    valid_roles = ['customer', 'restaurant_owner', 'delivery_partner', 'admin']
    if new_role in valid_roles:
        user.role = new_role
        db.session.commit()
        flash(f'Role for {user.email} changed to {new_role}.', 'success')
    else:
        flash('Invalid role provided.', 'danger')
    return redirect(request.referrer or url_for('admin.users'))

@admin.route('/menu')
@login_required
@role_required('admin')
def menu():
    hotel_filter = request.args.get('hotel_id', type=int)
    search_query = request.args.get('q', '').strip()
    veg_filter = request.args.get('veg')
    
    query = FoodItem.query.options(
        joinedload(FoodItem.restaurant),
        joinedload(FoodItem.category)
    )
    if hotel_filter:
        query = query.filter(FoodItem.restaurant_id == hotel_filter)
    if veg_filter == 'veg':
        query = query.filter(FoodItem.is_vegetarian == True)
    elif veg_filter == 'non-veg':
        query = query.filter(FoodItem.is_vegetarian == False)
    if search_query:
        query = query.filter(FoodItem.name.ilike(f'%{search_query}%'))
        
    foods = query.order_by(FoodItem.created_at.desc()).all()
    all_hotels = Restaurant.query.all()
    
    return render_template(
        'admin/menu.html',
        foods=foods,
        hotels=all_hotels,
        selected_hotel=hotel_filter,
        search_query=search_query,
        veg_filter=veg_filter
    )

@admin.route('/menu/<int:item_id>/toggle', methods=['POST'])
@login_required
@role_required('admin')
def toggle_food_item(item_id):
    item = FoodItem.query.get_or_404(item_id)
    item.is_available = not item.is_available
    db.session.commit()
    status_text = 'available' if item.is_available else 'unavailable'
    flash(f'Item "{item.name}" marked as {status_text}.', 'success')
    return redirect(request.referrer or url_for('admin.menu'))

@admin.route('/delivery_partners')
@login_required
@role_required('admin')
def delivery_partners():
    partners = User.query.filter_by(role='delivery_partner').all()
    if partners:
        p_ids = [p.id for p in partners]
        active_orders = Order.query.options(
            joinedload(Order.restaurant),
            joinedload(Order.customer)
        ).filter(
            Order.delivery_partner_id.in_(p_ids),
            Order.order_status.in_(['READY_FOR_PICKUP', 'OUT_FOR_DELIVERY'])
        ).all()
        
        delivered_stats = db.session.query(
            Order.delivery_partner_id,
            func.count(Order.id),
            func.sum(Order.delivery_fee)
        ).filter(
            Order.delivery_partner_id.in_(p_ids),
            Order.order_status == 'DELIVERED'
        ).group_by(Order.delivery_partner_id).all()
        
        delivered_map = {r[0]: (r[1], float(r[2] or 0)) for r in delivered_stats}
        
        for p in partners:
            p.active_deliveries = [o for o in active_orders if o.delivery_partner_id == p.id]
            p.completed_deliveries_count = delivered_map.get(p.id, (0, 0))[0]
            p.earnings = delivered_map.get(p.id, (0, 0))[1]
            
    return render_template('admin/delivery_partners.html', partners=partners)
