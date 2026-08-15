from flask import render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from app import db
from app.customer import customer
from app.customer.forms import AddressForm, CheckoutForm
from app.models import Restaurant, FoodCategory, FoodItem, Cart, CartItem, Address, Order, OrderItem, OrderStatusHistory, Payment
import razorpay

def get_or_create_cart():
    cart = Cart.query.options(
        joinedload(Cart.items).joinedload(CartItem.food_item)
    ).filter_by(user_id=current_user.id).first()
    
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()
    return cart

@customer.route('/')
def home():
    # Eager load restaurant to avoid N+1 query latency
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
        
    # Eager load food items for all categories in a single query
    categories = FoodCategory.query.options(
        joinedload(FoodCategory.food_items)
    ).filter_by(restaurant_id=restaurant_id, is_active=True).order_by(FoodCategory.display_order).all()
    
    return render_template('customer/restaurant_detail.html', restaurant=restaurant, categories=categories)

@customer.route('/add_to_cart/<int:item_id>', methods=['POST'])
@login_required
def add_to_cart(item_id):
    if current_user.role != 'customer':
        flash('Only customers can place orders.', 'danger')
        return redirect(url_for('customer.home'))
        
    food = FoodItem.query.get_or_404(item_id)
    cart = get_or_create_cart()
    
    if cart.restaurant_id and cart.restaurant_id != food.restaurant_id and cart.items:
        if request.form.get('confirm_clear') == 'yes':
            for i in cart.items:
                db.session.delete(i)
            cart.restaurant_id = food.restaurant_id
        else:
            flash('Your cart contains items from another hotel. Please clear your cart first to order from this hotel.', 'warning')
            return redirect(url_for('customer.cart'))
    else:
        cart.restaurant_id = food.restaurant_id
        
    cart_item = CartItem.query.filter_by(cart_id=cart.id, food_item_id=food.id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart.id, food_item_id=food.id, quantity=1)
        db.session.add(cart_item)
        
    db.session.commit()
    flash(f'{food.name} added to cart.', 'success')
    return redirect(url_for('customer.restaurant_detail', restaurant_id=food.restaurant_id))

@customer.route('/cart')
@login_required
def cart():
    cart = get_or_create_cart()
    subtotal = sum(item.food_item.price * item.quantity for item in cart.items)
    delivery_fee = 0
    tax = 0
    if cart.restaurant_id and cart.items:
        restaurant = Restaurant.query.get(cart.restaurant_id)
        if restaurant:
            delivery_fee = restaurant.delivery_fee
            tax = subtotal * 0.05 # 5% tax
    
    total = subtotal + delivery_fee + tax
    return render_template('customer/cart.html', cart=cart, subtotal=subtotal, delivery_fee=delivery_fee, tax=tax, total=total)

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
        
    restaurant = Restaurant.query.get(cart.restaurant_id)
    subtotal = sum(item.food_item.price * item.quantity for item in cart.items)
    
    if subtotal < restaurant.minimum_order:
        flash(f'Minimum order amount for {restaurant.name} is ₹{restaurant.minimum_order:.2f}', 'danger')
        return redirect(url_for('customer.cart'))
        
    tax = subtotal * 0.05
    total = subtotal + restaurant.delivery_fee + tax
    
    addresses = Address.query.filter_by(user_id=current_user.id).all()
    form = CheckoutForm()
    form.address_id.choices = [(a.id, f"{a.name} - {a.address_line1}, {a.city}") for a in addresses]
    
    if form.validate_on_submit():
        try:
            order = Order(
                customer_id=current_user.id,
                restaurant_id=restaurant.id,
                address_id=form.address_id.data,
                subtotal=subtotal,
                delivery_fee=restaurant.delivery_fee,
                tax=tax,
                total_amount=total,
                special_instructions=form.special_instructions.data,
                payment_status='PENDING',
                order_status='PLACED'
            )
            db.session.add(order)
            db.session.flush() 
            
            for item in cart.items:
                order_item = OrderItem(
                    order_id=order.id,
                    food_item_id=item.food_item_id,
                    quantity=item.quantity,
                    price=item.food_item.price
                )
                db.session.add(order_item)
                db.session.delete(item) 
            
            cart.restaurant_id = None
            
            history = OrderStatusHistory(order_id=order.id, status='PLACED', changed_by=current_user.id, message='Order placed by customer')
            db.session.add(history)
            
            payment = Payment(
                order_id=order.id,
                gateway=form.payment_method.data,
                amount=total,
                payment_method=form.payment_method.data,
                status='PENDING'
            )
            db.session.add(payment)
            db.session.commit()
            
            if form.payment_method.data == 'razorpay':
                return redirect(url_for('customer.payment', order_id=order.id))
            else:
                flash('Order placed successfully with Cash on Delivery.', 'success')
                return redirect(url_for('customer.orders'))
                
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while placing the order. Please try again.', 'danger')
            current_app.logger.error(f'Order error: {e}')
            
    return render_template('customer/checkout.html', form=form, cart=cart, subtotal=subtotal, tax=tax, total=total, restaurant=restaurant, addresses=addresses)

@customer.route('/payment/<int:order_id>')
@login_required
def payment(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id:
        abort(403)
        
    client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
    
    razorpay_order = client.order.create({
        'amount': int(order.total_amount * 100),
        'currency': 'INR',
        'receipt': str(order.id)
    })
    
    order.payment.gateway_order_id = razorpay_order['id']
    db.session.commit()
    
    return render_template('customer/payment.html', order=order, razorpay_order_id=razorpay_order['id'], razorpay_key=current_app.config['RAZORPAY_KEY_ID'])

@customer.route('/payment/verify', methods=['POST'])
@login_required
def payment_verify():
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')
    order_id = request.form.get('order_id')
    
    order = Order.query.get_or_404(order_id)
    
    client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], current_app.config['RAZORPAY_KEY_SECRET']))
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
        
        order.payment.status = 'SUCCESS'
        order.payment.transaction_id = razorpay_payment_id
        order.payment.paid_at = db.func.current_timestamp()
        order.payment_status = 'SUCCESS'
        
        history = OrderStatusHistory(order_id=order.id, status='CONFIRMED', message='Payment successful, order confirmed.')
        order.order_status = 'CONFIRMED'
        db.session.add(history)
        
        db.session.commit()
        flash('Payment successful! Your order is confirmed.', 'success')
    except razorpay.errors.SignatureVerificationError:
        order.payment.status = 'FAILED'
        order.payment_status = 'FAILED'
        db.session.commit()
        flash('Payment verification failed.', 'danger')
        
    return redirect(url_for('customer.orders'))

@customer.route('/orders')
@login_required
def orders():
    my_orders = Order.query.options(
        joinedload(Order.items).joinedload(OrderItem.food_item),
        joinedload(Order.restaurant)
    ).filter_by(customer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('customer/orders.html', orders=my_orders)

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
