from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from database import init_db, get_db
from auth import User
import requests
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'fallback-secret-key')

PAYSTACK_SECRET = os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC = os.getenv('PAYSTACK_PUBLIC_KEY')

# ── FLASK LOGIN SETUP ──────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to continue.'

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# ── AUTH ROUTES ────────────────────────────────────────

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email     = request.form.get('email')
        phone     = request.form.get('phone')
        password  = request.form.get('password')
        confirm   = request.form.get('confirm_password')

        if password != confirm:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('signup'))

        db = get_db()
        existing = db.execute(
            'SELECT id FROM users WHERE email = ?', (email,)
        ).fetchone()

        if existing:
            flash('Email already registered. Please log in.', 'error')
            db.close()
            return redirect(url_for('login'))

        db.execute('''
            INSERT INTO users (full_name, email, phone, password)
            VALUES (?, ?, ?, ?)
        ''', (full_name, email, phone, generate_password_hash(password)))
        db.commit()
        db.close()

        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')

        user_row = User.get_by_email(email)

        if not user_row or not check_password_hash(user_row['password'], password):
            flash('Invalid email or password.', 'error')
            return redirect(url_for('login'))

        user = User(
            id=user_row['id'],
            full_name=user_row['full_name'],
            email=user_row['email'],
            phone=user_row['phone'],
            role=user_row['role']
        )
        login_user(user)

        if user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# ── MAIN ROUTES ────────────────────────────────────────

@app.route('/')
@login_required
def index():
    db = get_db()
    items = db.execute('SELECT * FROM menu_items').fetchall()
    db.close()
    return render_template('index.html', items=items)


@app.route('/order/<int:item_id>')
@login_required
def order(item_id):
    db = get_db()
    item = db.execute(
        'SELECT * FROM menu_items WHERE id = ?', (item_id,)
    ).fetchone()
    db.close()
    return render_template('order.html', item=item)


@app.route('/place-order', methods=['POST'])
@login_required
def place_order():
    item_id  = request.form.get('item_id')
    quantity = int(request.form.get('quantity'))
    address  = request.form.get('delivery_address')

    db = get_db()
    item        = db.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    total_price = item['price'] * quantity
    delivery_fee = item['delivery_fee']

    db.execute('''
        INSERT INTO orders
        (user_id, item_id, quantity, total_price, delivery_fee, delivery_address)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (current_user.id, item_id, quantity, total_price, delivery_fee, address))
    db.commit()

    order = db.execute('SELECT last_insert_rowid() as id').fetchone()
    order_id = order['id']
    db.close()

    return redirect(url_for('payment', order_id=order_id))


# ── PAYMENT ROUTES ─────────────────────────────────────

@app.route('/payment/<int:order_id>')
@login_required
def payment(order_id):
    db = get_db()
    order = db.execute('''
        SELECT orders.*, menu_items.name as item_name
        FROM orders JOIN menu_items ON orders.item_id = menu_items.id
        WHERE orders.id = ? AND orders.user_id = ?
    ''', (order_id, current_user.id)).fetchone()
    db.close()

    if not order:
        flash('Order not found.', 'error')
        return redirect(url_for('index'))

    grand_total = order['total_price'] + order['delivery_fee']
    return render_template('payment.html',
        order=order,
        grand_total=grand_total,
        paystack_public_key=PAYSTACK_PUBLIC
    )


@app.route('/verify-payment/<int:order_id>')
@login_required
def verify_payment(order_id):
    reference = request.args.get('reference')

    response = requests.get(
        f'https://api.paystack.co/transaction/verify/{reference}',
        headers={'Authorization': f'Bearer {PAYSTACK_SECRET}'}
    )
    data = response.json()

    if data['status'] and data['data']['status'] == 'success':
        db = get_db()
        db.execute('''
            UPDATE orders
            SET payment_status = "paid", payment_reference = ?, order_status = "confirmed"
            WHERE id = ?
        ''', (reference, order_id))

        # Initialize tracker
        db.execute('''
            INSERT INTO tracker_stages (order_id, stage, label)
            VALUES (?, 0, "Order Confirmed")
        ''', (order_id,))
        db.commit()
        db.close()

        flash('Payment successful! Your order is confirmed.', 'success')
        return redirect(url_for('tracker', order_id=order_id))

    flash('Payment verification failed. Please try again.', 'error')
    return redirect(url_for('payment', order_id=order_id))


# ── TRACKER ROUTE ──────────────────────────────────────

@app.route('/tracker/<int:order_id>')
@login_required
def tracker(order_id):
    db = get_db()
    order = db.execute('''
        SELECT orders.*, menu_items.name as item_name,
               users.full_name as customer_name
        FROM orders
        JOIN menu_items ON orders.item_id = menu_items.id
        JOIN users ON orders.user_id = users.id
        WHERE orders.id = ?
    ''', (order_id,)).fetchone()

    stages = db.execute('''
        SELECT * FROM tracker_stages
        WHERE order_id = ? ORDER BY stage ASC
    ''', (order_id,)).fetchall()
    db.close()

    return render_template('tracker.html', order=order, stages=stages)


@app.route('/api/tracker/<int:order_id>')
@login_required
def tracker_api(order_id):
    db = get_db()
    order = db.execute(
        'SELECT * FROM orders WHERE id = ?', (order_id,)
    ).fetchone()
    stages = db.execute(
        'SELECT * FROM tracker_stages WHERE order_id = ? ORDER BY stage ASC',
        (order_id,)
    ).fetchall()
    db.close()

    return jsonify({
        'order_status': order['order_status'],
        'tracker_stage': order['tracker_stage'],
        'stages': [{'stage': s['stage'], 'label': s['label'],
                    'timestamp': s['timestamp']} for s in stages]
    })


# ── USER DASHBOARD ─────────────────────────────────────

@app.route('/dashboard')
@login_required
def user_dashboard():
    db = get_db()
    orders = db.execute('''
        SELECT orders.*, menu_items.name as item_name
        FROM orders JOIN menu_items ON orders.item_id = menu_items.id
        WHERE orders.user_id = ?
        ORDER BY orders.created_at DESC
    ''', (current_user.id,)).fetchall()
    db.close()
    return render_template('user_dashboard.html', orders=orders)


# ── ADMIN ROUTES ───────────────────────────────────────

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('index'))

    db = get_db()
    orders = db.execute('''
        SELECT orders.*, menu_items.name as item_name,
               users.full_name as customer_name,
               users.phone as customer_phone
        FROM orders
        JOIN menu_items ON orders.item_id = menu_items.id
        JOIN users ON orders.user_id = users.id
        ORDER BY orders.created_at DESC
    ''').fetchall()

    total_revenue = db.execute(
        'SELECT SUM(total_price + delivery_fee) FROM orders WHERE payment_status = "paid"'
    ).fetchone()[0] or 0

    total_orders = db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    pending      = db.execute('SELECT COUNT(*) FROM orders WHERE order_status = "pending"').fetchone()[0]
    db.close()

    return render_template('admin_dashboard.html',
        orders=orders,
        total_revenue=total_revenue,
        total_orders=total_orders,
        pending=pending
    )


@app.route('/admin/update-order/<int:order_id>', methods=['POST'])
@login_required
def admin_update_order(order_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    new_status = request.form.get('order_status')

    stage_map = {
        'confirmed':    (0, 'Order Confirmed'),
        'preparing':    (1, 'Preparing Your Food'),
        'on the way':   (2, 'Rider On The Way'),
        'delivered':    (3, 'Order Delivered')
    }

    db = get_db()
    db.execute(
        'UPDATE orders SET order_status = ?, tracker_stage = ? WHERE id = ?',
        (new_status, stage_map.get(new_status, (0, ''))[0], order_id)
    )

    existing = db.execute(
        'SELECT id FROM tracker_stages WHERE order_id = ? AND stage = ?',
        (order_id, stage_map.get(new_status, (0,))[0])
    ).fetchone()

    if not existing:
        db.execute('''
            INSERT INTO tracker_stages (order_id, stage, label)
            VALUES (?, ?, ?)
        ''', (order_id, stage_map[new_status][0], stage_map[new_status][1]))

    db.commit()
    db.close()

    flash(f'Order #{order_id} updated to {new_status}.', 'success')
    return redirect(url_for('admin_dashboard'))


# ── START ──────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True)