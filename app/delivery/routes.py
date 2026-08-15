from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.delivery import delivery
from app.models import Order, OrderStatusHistory
from app.utils.decorators import role_required

@delivery.route('/dashboard')
@login_required
@role_required('delivery_partner')
def dashboard():
    # Available orders (Ready for pickup, no partner assigned)
    available_orders = Order.query.filter_by(order_status='READY_FOR_PICKUP', delivery_partner_id=None).all()
    
    # Active orders for this partner
    active_orders = Order.query.filter(
        Order.delivery_partner_id == current_user.id,
        Order.order_status.in_(['READY_FOR_PICKUP', 'OUT_FOR_DELIVERY'])
    ).all()
    
    # Completed orders for this partner
    completed_orders = Order.query.filter_by(
        delivery_partner_id=current_user.id,
        order_status='DELIVERED'
    ).order_by(Order.updated_at.desc()).limit(10).all()
    
    return render_template('delivery/dashboard.html', available_orders=available_orders, active_orders=active_orders, completed_orders=completed_orders)

@delivery.route('/order/<int:order_id>/accept', methods=['POST'])
@login_required
@role_required('delivery_partner')
def accept_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.delivery_partner_id is not None or order.order_status != 'READY_FOR_PICKUP':
        flash('This order is no longer available.', 'warning')
        return redirect(url_for('delivery.dashboard'))
        
    order.delivery_partner_id = current_user.id
    history = OrderStatusHistory(order_id=order.id, status='OUT_FOR_DELIVERY', changed_by=current_user.id, message='Order picked up by delivery partner')
    order.order_status = 'OUT_FOR_DELIVERY'
    
    db.session.add(history)
    db.session.commit()
    
    flash(f'You have accepted order {order.order_number}.', 'success')
    return redirect(url_for('delivery.dashboard'))

@delivery.route('/order/<int:order_id>/deliver', methods=['POST'])
@login_required
@role_required('delivery_partner')
def mark_delivered(order_id):
    order = Order.query.get_or_404(order_id)
    if order.delivery_partner_id != current_user.id:
        flash('You are not assigned to this order.', 'danger')
        return redirect(url_for('delivery.dashboard'))
        
    history = OrderStatusHistory(order_id=order.id, status='DELIVERED', changed_by=current_user.id, message='Order delivered successfully')
    order.order_status = 'DELIVERED'
    
    if order.payment and order.payment_status == 'PENDING' and order.payment.gateway == 'cod':
        order.payment_status = 'SUCCESS'
        order.payment.status = 'SUCCESS'
        order.payment.paid_at = db.func.current_timestamp()
    
    db.session.add(history)
    db.session.commit()
    
    flash(f'Order {order.order_number} marked as delivered.', 'success')
    return redirect(url_for('delivery.dashboard'))
