import sqlite3

def init_db():
    conn = sqlite3.connect('delivery.db')
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Menu items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            delivery_fee REAL DEFAULT 500.00,
            image_url TEXT
        )
    ''')

    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            delivery_fee REAL NOT NULL,
            delivery_address TEXT NOT NULL,
            payment_status TEXT DEFAULT 'unpaid',
            payment_reference TEXT,
            order_status TEXT DEFAULT 'pending',
            tracker_stage INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (item_id) REFERENCES menu_items(id)
        )
    ''')

    # Tracker stages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracker_stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            stage INTEGER NOT NULL,
            label TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    ''')

    # Seed menu items
    cursor.execute('SELECT COUNT(*) FROM menu_items')
    if cursor.fetchone()[0] == 0:
        items = [
            ('Jollof Rice', 'Delicious Nigerian jollof rice with chicken', 1500.00, 500.00, ''),
            ('Fried Rice', 'Special fried rice with assorted proteins', 1800.00, 500.00, ''),
            ('Pounded Yam & Egusi', 'Smooth pounded yam with rich egusi soup', 2000.00, 500.00, ''),
            ('Suya Platter', 'Spicy grilled beef suya with onions', 1200.00, 500.00, ''),
            ('Moi Moi', 'Steamed bean pudding with eggs and fish', 800.00, 500.00, ''),
        ]
        cursor.executemany(
            'INSERT INTO menu_items (name, description, price, delivery_fee, image_url) VALUES (?, ?, ?, ?, ?)',
            items
        )

    # Seed default admin account
    cursor.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    if cursor.fetchone()[0] == 0:
        from werkzeug.security import generate_password_hash
        cursor.execute('''
            INSERT INTO users (full_name, email, phone, password, role)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            'Admin',
            'admin@quickdeliver.com',
            '08000000000',
            generate_password_hash('admin123'),
            'admin'
        ))
    # these 3 lines must be INSIDE init_db() — indented with 4 spaces
    conn.commit()
    conn.close()
    print("Database initialized!")

# these lines must be OUTSIDE init_db() — no indentation
def get_db():
    conn = sqlite3.connect('delivery.db')
    conn.row_factory = sqlite3.Row
    return conn

# this must also be OUTSIDE — no indentation
if __name__ == '__main__':
    init_db()