from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
from database import init_db

app = Flask(__name__)

# Helper function to connect to database
def get_db():
    conn = sqlite3.connect('delivery.db')
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn

# ─── ROUTES ───────────────────────────────────────────

# Home page — show menu
@app.route('/')
def index():
    db = get_db()
    items = db.execute('SELECT * FROM menu_items').fetchall()
    db.close()
    return render_template('index.html', items=items)

# Place order page
@app.route('/order/<int:item_id>')
def order(item_id):
    db = get_db()
    item = db.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    db.close()
    return render_template('order.html', item=item)

# Submit order
@app.route('/place-order', methods=['POST'])
def place_order():
    data = request.form
    item_id = data.get('item_id')
    quantity = int(data.get('quantity'))

    db = get_db()
    item = db.execute('SELECT * FROM menu_items WHERE id = ?', (item_id,)).fetchone()
    total_price = item['price'] * quantity

    db.execute('''
        INSERT INTO orders (customer_name, customer_address, customer_phone, item_id, quantity, total_price)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        data.get('customer_name'),
        data.get('customer_address'),
        data.get('customer_phone'),
        item_id,
        quantity,
        total_price
    ))
    db.commit()

    # Get the last inserted order id
    order = db.execute('SELECT last_insert_rowid() as id').fetchone()
    order_id = order['id']
    db.close()

    return redirect(url_for('status', order_id=order_id))

# Order status page
@app.route('/status/<int:order_id>')
def status(order_id):
    db = get_db()
    order = db.execute('''
        SELECT orders.*, menu_items.name as item_name
        FROM orders
        JOIN menu_items ON orders.item_id = menu_items.id
        WHERE orders.id = ?
    ''', (order_id,)).fetchone()
    db.close()
    return render_template('status.html', order=order)

# Admin — update order status
@app.route('/update-status/<int:order_id>', methods=['POST'])
def update_status(order_id):
    new_status = request.form.get('status')
    db = get_db()
    db.execute('UPDATE orders SET status = ? WHERE id = ?', (new_status, order_id))
    db.commit()
    db.close()
    return redirect(url_for('status', order_id=order_id))

# ─── START APP ────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=True)