import sqlite3

def init_db():
    conn = sqlite3.connect('delivery.db')
    cursor = conn.cursor()

    # Create menu items table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            image_url TEXT
        )
    ''')

    # Create orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_address TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES menu_items (id)
        )
    ''')

    # Add sample menu items if table is empty
    cursor.execute('SELECT COUNT(*) FROM menu_items')
    if cursor.fetchone()[0] == 0:
        sample_items = [
            ('Jollof Rice', 'Delicious Nigerian jollof rice with chicken', 1500.00, ''),
            ('Fried Rice', 'Special fried rice with assorted proteins', 1800.00, ''),
            ('Pounded Yam & Egusi', 'Smooth pounded yam with rich egusi soup', 2000.00, ''),
            ('Suya Platter', 'Spicy grilled beef suya with onions', 1200.00, ''),
            ('Moi Moi', 'Steamed bean pudding with eggs and fish', 800.00, ''),
        ]
        cursor.executemany(
            'INSERT INTO menu_items (name, description, price, image_url) VALUES (?, ?, ?, ?)',
            sample_items
        )

    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == '__main__':
    init_db()