from flask import render_template, redirect, url_for, flash, request, current_app, abort, jsonify, session
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import db
from app.customer import customer
from app.customer.forms import AddressForm, CheckoutForm
from app.models import Restaurant, FoodCategory, FoodItem, Cart, CartItem, Address, Order, OrderItem, OrderStatusHistory, Payment
import razorpay

def get_or_create_cart():
    cart = Cart.query.options(
        joinedload(Cart.items).joinedload(CartItem.food_item).joinedload(FoodItem.restaurant)
    ).filter_by(user_id=current_user.id).first()
    
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()
    return cart

@customer.route('/ping', methods=['GET', 'HEAD'])
@customer.route('/health', methods=['GET', 'HEAD'])
@customer.route('/keep-alive', methods=['GET', 'HEAD'])
def ping():
    from app.api.routes import keep_alive
    return keep_alive()

@customer.route('/')
def home():
    popular_foods = FoodItem.query.options(
        joinedload(FoodItem.restaurant)
    ).filter_by(is_available=True).limit(8).all()
    return render_template('customer/home.html', foods=popular_foods)

@customer.route('/restaurants')
def restaurants():
    search = request.args.get('search', '').strip()
    if search:
        all_restaurants = Restaurant.query.filter(
            Restaurant.is_active == True,
            (Restaurant.name.ilike(f'%{search}%')) | (Restaurant.cuisine_type.ilike(f'%{search}%'))
        ).all()
    else:
        all_restaurants = Restaurant.query.filter_by(is_active=True).all()
    return render_template('customer/restaurants.html', restaurants=all_restaurants, search=search)

@customer.route('/restaurant/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    if not restaurant.is_active:
        flash('This hotel is currently unavailable.', 'warning')
        return redirect(url_for('customer.restaurants'))
        
    categories = FoodCategory.query.options(
        joinedload(FoodCategory.food_items)
    ).filter_by(restaurant_id=restaurant_id, is_active=True).order_by(FoodCategory.display_order).all()
    
    return render_template('customer/restaurant_detail.html', restaurant=restaurant, categories=categories)

@customer.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json
    
    if not current_user.is_authenticated:
        if is_ajax:
            return jsonify({'success': False, 'redirect': url_for('auth.login'), 'message': 'Please login to add items to cart.'}), 401
        flash('Please login to add items to your cart.', 'info')
        return redirect(url_for('auth.login'))

    if current_user.role != 'customer':
        if is_ajax:
            return jsonify({'success': False, 'message': 'Only customers can place orders.'}), 403
        flash('Only customers can place orders.', 'danger')
        return redirect(url_for('customer.home'))
        
    food = FoodItem.query.get_or_404(item_id)
    cart = get_or_create_cart()
    
    # Multi-Hotel Support: Allow food items from any hotel in the same cart
    cart_item = CartItem.query.filter_by(cart_id=cart.id, food_item_id=food.id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart.id, food_item_id=food.id, quantity=1)
        db.session.add(cart_item)
        
    db.session.commit()
    
    total_cart_items = sum(i.quantity for i in cart.items)
    
    if is_ajax:
        return jsonify({
            'success': True,
            'message': f'{food.name} added to cart!',
            'cart_count': total_cart_items
        })
        
    flash(f'{food.name} added to cart.', 'success')
    return redirect(request.referrer or url_for('customer.restaurant_detail', restaurant_id=food.restaurant_id))

@customer.route('/cart')
@login_required
def cart():
    cart = get_or_create_cart()
    
    # Group items by Hotel/Restaurant
    hotel_groups = {}
    for item in cart.items:
        hotel = item.food_item.restaurant
        if hotel not in hotel_groups:
            hotel_groups[hotel] = []
        hotel_groups[hotel].append(item)
        
    subtotal = sum(item.food_item.price * item.quantity for item in cart.items)
    
    # Customer-friendly delivery calculation (max delivery fee among chosen hotels, default 40)
    delivery_fee = max([h.delivery_fee for h in hotel_groups.keys()], default=0.0) if hotel_groups else 0.0
    tax = subtotal * 0.05 # 5% GST
    total = subtotal + delivery_fee + tax
    
    return render_template(
        'customer/cart.html',
        cart=cart,
        hotel_groups=hotel_groups,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        tax=tax,
        total=total
    )

@customer.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    cart = get_or_create_cart()
    for item in cart.items:
        db.session.delete(item)
    cart.restaurant_id = None
    db.session.commit()
    flash('Cart cleared.', 'info')
    return redirect(url_for('customer.cart'))

@customer.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.cart.user_id != current_user.id:
        abort(403)
        
    action = request.form.get('action')
    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease':
        cart_item.quantity -= 1
        if cart_item.quantity <= 0:
            db.session.delete(cart_item)
    elif action == 'remove':
        db.session.delete(cart_item)
        
    db.session.commit()
    return redirect(url_for('customer.cart'))

@customer.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = get_or_create_cart()
    if not cart.items:
        flash('Your cart is empty.', 'info')
        return redirect(url_for('customer.cart'))
        
    # Group items by Hotel/Restaurant
    hotel_groups = {}
    for item in cart.items:
        hotel = item.food_item.restaurant
        if hotel not in hotel_groups:
            hotel_groups[hotel] = []
        hotel_groups[hotel].append(item)
        
    subtotal = sum(item.food_item.price * item.quantity for item in cart.items)
    delivery_fee = max([h.delivery_fee for h in hotel_groups.keys()], default=0.0) if hotel_groups else 0.0
    tax = subtotal * 0.05
    total = subtotal + delivery_fee + tax
    
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    form = CheckoutForm()
    form.address_id.choices = [(a.id, f"{a.name} - {a.address_line1}, {a.city}") for a in addresses]
    
    if form.validate_on_submit():
        try:
            created_orders = []
            num_hotels = len(hotel_groups)
            # Apportion delivery fee fairly per hotel
            per_hotel_delivery = round(delivery_fee / num_hotels, 2) if num_hotels > 0 else 0.0
            
            for hotel, items in hotel_groups.items():
                h_subtotal = sum(i.food_item.price * i.quantity for i in items)
                h_tax = round(h_subtotal * 0.05, 2)
                h_total = h_subtotal + per_hotel_delivery + h_tax
                
                order = Order(
                    customer_id=current_user.id,
                    restaurant_id=hotel.id,
                    address_id=form.address_id.data,
                    subtotal=h_subtotal,
                    delivery_fee=per_hotel_delivery,
                    tax=h_tax,
                    total_amount=h_total,
                    special_instructions=form.special_instructions.data,
                    payment_status='PENDING',
                    order_status='PLACED'
                )
                db.session.add(order)
                db.session.flush() # get order.id
                
                for item in items:
                    order_item = OrderItem(
                        order_id=order.id,
                        food_item_id=item.food_item_id,
                        quantity=item.quantity,
                        price=item.food_item.price
                    )
                    db.session.add(order_item)
                    db.session.delete(item)
                    
                history = OrderStatusHistory(
                    order_id=order.id,
                    status='PLACED',
                    changed_by=current_user.id,
                    message=f'Order placed with {hotel.name}'
                )
                db.session.add(history)
                
                payment = Payment(
                    order_id=order.id,
                    gateway=form.payment_method.data,
                    amount=h_total,
                    payment_method=form.payment_method.data,
                    status='PENDING'
                )
                db.session.add(payment)
                created_orders.append(order)
                
            cart.restaurant_id = None
            db.session.commit()
            
            if form.payment_method.data == 'razorpay':
                session['checkout_order_ids'] = [o.id for o in created_orders]
                return redirect(url_for('customer.payment_multi'))
            else:
                hotel_count = len(created_orders)
                if hotel_count > 1:
                    flash(f'Successfully placed {hotel_count} orders across your selected hotels with Cash on Delivery!', 'success')
                else:
                    flash('Order placed successfully with Cash on Delivery.', 'success')
                return redirect(url_for('customer.orders'))
                
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while placing the order. Please try again.', 'danger')
            current_app.logger.error(f'Multi-order error: {e}')
            
    return render_template(
        'customer/checkout.html',
        form=form,
        cart=cart,
        hotel_groups=hotel_groups,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        tax=tax,
        total=total,
        addresses=addresses
    )

@customer.route('/payment/multi')
@login_required
def payment_multi():
    order_ids = session.get('checkout_order_ids', [])
    if not order_ids:
        flash('No active checkout session found.', 'warning')
        return redirect(url_for('customer.orders'))
        
    orders = Order.query.filter(Order.id.in_(order_ids), Order.customer_id == current_user.id).all()
    if not orders:
        flash('Orders not found.', 'danger')
        return redirect(url_for('customer.orders'))
        
    grand_total = sum(o.total_amount for o in orders)
    
    client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
    
    razorpay_order = client.order.create({
        'amount': int(round(grand_total * 100)),
        'currency': 'INR',
        'receipt': f"BATCH-{orders[0].id}"
    })
    
    for o in orders:
        if o.payment:
            o.payment.gateway_order_id = razorpay_order['id']
    db.session.commit()
    
    return render_template(
        'customer/payment.html',
        order=orders[0],
        orders=orders,
        grand_total=grand_total,
        razorpay_order_id=razorpay_order['id'],
        razorpay_key=current_app.config['RAZORPAY_KEY_ID']
    )

@customer.route('/payment/<int:order_id>')
@login_required
def payment(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        abort(403)
        
    client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
    
    razorpay_order = client.order.create({
        'amount': int(round(order.total_amount * 100)),
        'currency': 'INR',
        'receipt': str(order.id)
    })
    
    if order.payment:
        order.payment.gateway_order_id = razorpay_order['id']
    db.session.commit()
    
    return render_template(
        'customer/payment.html',
        order=order,
        grand_total=order.total_amount,
        razorpay_order_id=razorpay_order['id'],
        razorpay_key=current_app.config['RAZORPAY_KEY_ID']
    )

@customer.route('/payment/verify', methods=['POST'])
@login_required
def payment_verify():
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')
    
    client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
        
        # Check if this payment was for a multi-order batch
        order_ids = session.pop('checkout_order_ids', None)
        if order_ids:
            orders = Order.query.filter(Order.id.in_(order_ids), Order.customer_id == current_user.id).all()
        else:
            order_id = request.form.get('order_id')
            orders = [Order.query.get(order_id)] if order_id else []
            
        for o in orders:
            if o:
                if o.payment:
                    o.payment.status = 'SUCCESS'
                    o.payment.transaction_id = razorpay_payment_id
                    o.payment.paid_at = db.func.current_timestamp()
                o.payment_status = 'SUCCESS'
                o.order_status = 'CONFIRMED'
                history = OrderStatusHistory(order_id=o.id, status='CONFIRMED', message='Online payment verified successfully.')
                db.session.add(history)
                
        db.session.commit()
        flash('Payment successful! Your order(s) are confirmed.', 'success')
        return redirect(url_for('customer.orders'))
        
    except razorpay.errors.SignatureVerificationError:
        order_ids = session.pop('checkout_order_ids', None)
        if order_ids:
            orders = Order.query.filter(Order.id.in_(order_ids)).all()
            for o in orders:
                if o.payment:
                    o.payment.status = 'FAILED'
                o.payment_status = 'FAILED'
            db.session.commit()
        flash('Payment verification failed.', 'danger')
        return redirect(url_for('customer.orders'))

@customer.route('/orders')
@login_required
def orders():
    my_orders = Order.query.options(
        joinedload(Order.items).joinedload(OrderItem.food_item),
        joinedload(Order.restaurant),
        joinedload(Order.address)
    ).filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('customer/orders.html', orders=my_orders)

@customer.route('/order/<int:order_id>/track')
@login_required
def track_order(order_id):
    order = Order.query.options(
        joinedload(Order.items).joinedload(OrderItem.food_item),
        joinedload(Order.restaurant),
        joinedload(Order.address),
        joinedload(Order.payment)
    ).filter_by(id=order_id).first_or_404()
    
    if order.customer_id != current_user.id and current_user.role != 'admin':
        abort(403)
        
    history = OrderStatusHistory.query.filter_by(order_id=order_id).order_by(OrderStatusHistory.created_at.asc()).all()
    
    stages = [
        {'key': 'PLACED', 'label': 'Order Placed', 'icon': 'bi-receipt'},
        {'key': 'CONFIRMED', 'label': 'Confirmed', 'icon': 'bi-check2-circle'},
        {'key': 'PREPARING', 'label': 'Preparing', 'icon': 'bi-egg-fried'},
        {'key': 'OUT_FOR_DELIVERY', 'label': 'On the Way', 'icon': 'bi-bicycle'},
        {'key': 'DELIVERED', 'label': 'Delivered', 'icon': 'bi-house-check-fill'}
    ]
    
    status_order = ['PLACED', 'CONFIRMED', 'PREPARING', 'READY_FOR_PICKUP', 'OUT_FOR_DELIVERY', 'DELIVERED']
    current_step = 0
    if order.order_status in status_order:
        idx = status_order.index(order.order_status)
        if idx >= 4:
            current_step = 3 if idx == 4 else 4
        elif idx == 3:
            current_step = 2
        else:
            current_step = idx
            
    is_cancelled = order.order_status in ['CANCELLED', 'REJECTED']

    return render_template(
        'customer/track_order.html',
        order=order,
        history=history,
        stages=stages,
        current_step=current_step,
        is_cancelled=is_cancelled
    )

@customer.route('/address/add', methods=['GET', 'POST'])
@login_required
def add_address():
    form = AddressForm()
    if form.validate_on_submit():
        address = Address(
            user_id=current_user.id,
            name=form.name.data,
            phone=form.phone.data,
            address_line1=form.address_line1.data,
            address_line2=form.address_line2.data,
            city=form.city.data,
            state=form.state.data,
            postal_code=form.postal_code.data,
            landmark=form.landmark.data,
            address_type=form.address_type.data
        )
        db.session.add(address)
        db.session.commit()
        
        next_page = request.args.get('next')
        if next_page == 'checkout':
            return redirect(url_for('customer.checkout'))
            
        flash('Address added successfully.', 'success')
        return redirect(url_for('customer.orders'))
        
    return render_template('customer/address_form.html', form=form)
