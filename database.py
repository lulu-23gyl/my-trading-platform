import sqlite3
import os
import streamlit as st

# 确保数据库目录存在
def init_db():
    conn = sqlite3.connect('second_hand_market.db')
    c = conn.cursor()
    
    # 创建用户表
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建商品表
    c.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description_zh TEXT,
        description_en TEXT,
        description_ja TEXT,
        description_ko TEXT,
        price REAL NOT NULL,
        category TEXT,
        condition TEXT,
        contact_info TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        image_path TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 为已有表添加多语言描述字段（兼容现有数据）
    try:
        c.execute('ALTER TABLE products ADD COLUMN description_zh TEXT')
        c.execute('ALTER TABLE products ADD COLUMN description_en TEXT')
        c.execute('ALTER TABLE products ADD COLUMN description_ja TEXT')
        c.execute('ALTER TABLE products ADD COLUMN description_ko TEXT')
        # 将现有description数据复制到description_zh（假设原数据为中文）
        c.execute('UPDATE products SET description_zh = description WHERE description IS NOT NULL')
    except sqlite3.OperationalError:
        # 如果字段已存在，则忽略错误
        pass
    
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
    
    # 创建索引以提高搜索性能
    c.execute('CREATE INDEX IF NOT EXISTS idx_products_title ON products(title)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_messages_sender_receiver ON messages(sender_id, receiver_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_messages_product ON messages(product_id)')
    
    # 创建密码重置表
    c.execute('''
    CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        code TEXT NOT NULL,
        expires_at TIMESTAMP NOT NULL,
        used BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 为密码重置表创建索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_password_resets_email ON password_resets(email)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_password_resets_expires ON password_resets(expires_at)')
    
    conn.commit()
    conn.close()

# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect('second_hand_market.db')
    conn.row_factory = sqlite3.Row  # 启用行工厂，方便按列名访问
    return conn

# 初始化数据库
# 无论数据库是否存在，都调用init_db()来确保所有表都已创建
init_db()
