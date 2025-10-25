import sqlite3

# 初始化消息表
def init_messages_table():
    conn = sqlite3.connect('second_hand_market.db')
    c = conn.cursor()
    
    # 创建消息表
    c.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        product_id INTEGER,
        content TEXT NOT NULL,
        is_read BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sender_id) REFERENCES users (id),
        FOREIGN KEY (receiver_id) REFERENCES users (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')
    
    # 创建索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_messages_sender_receiver ON messages(sender_id, receiver_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_messages_product ON messages(product_id)')
    
    conn.commit()
    conn.close()
    print("消息表初始化成功！")

if __name__ == "__main__":
    init_messages_table()