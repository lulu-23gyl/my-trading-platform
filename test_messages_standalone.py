# 独立测试脚本：测试消息获取和显示功能
import sqlite3
import datetime

# 模拟数据库连接函数
def get_db_connection():
    conn = sqlite3.connect('instance/database.db')
    conn.row_factory = sqlite3.Row  # 允许通过列名访问
    return conn

# 简化版的get_message_history函数
def get_message_history(user_id1, user_id2, product_id=None):
    print(f"\n测试消息获取：用户 {user_id1} 和用户 {user_id2} 之间的消息")
    
    conn = get_db_connection()
    
    # 构建查询
    query = """
    SELECT m.*, u.username as sender_name 
    FROM messages m 
    JOIN users u ON m.sender_id = u.id 
    WHERE (m.sender_id = ? AND m.receiver_id = ?) 
       OR (m.sender_id = ? AND m.receiver_id = ?)
    """
    params = [user_id1, user_id2, user_id2, user_id1]
    
    # 如果指定了商品ID
    if product_id:
        query += " AND m.product_id = ?"
        params.append(product_id)
    
    query += " ORDER BY m.created_at ASC"
    
    print(f"执行查询: {query}")
    print(f"参数: {params}")
    
    # 执行查询
    messages = conn.execute(query, params).fetchall()
    
    print(f"找到 {len(messages)} 条消息")
    
    # 打印消息详情
    for i, msg in enumerate(messages, 1):
        print(f"\n消息 {i}:")
        print(f"  ID: {msg['id']}")
        print(f"  发送者ID: {msg['sender_id']}")
        print(f"  接收者ID: {msg['receiver_id']}")
        print(f"  内容: {msg['content']}")
        print(f"  时间: {msg['created_at']}")
        if 'sender_name' in msg:
            print(f"  发送者用户名: {msg['sender_name']}")
    
    conn.close()
    return messages

# 测试用户表
def test_users_table():
    print("\n=== 测试用户表 ===")
    conn = get_db_connection()
    users = conn.execute("SELECT id, username FROM users").fetchall()
    print(f"找到 {len(users)} 个用户:")
    for user in users:
        print(f"  ID: {user['id']}, 用户名: {user['username']}")
    conn.close()

# 测试消息表
def test_messages_table():
    print("\n=== 测试消息表 ===")
    conn = get_db_connection()
    
    # 获取表结构
    cursor = conn.execute("PRAGMA table_info(messages)")
    columns = cursor.fetchall()
    print("消息表结构:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
    
    # 获取所有消息数量
    count = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    print(f"消息总数: {count}")
    
    # 获取前5条消息
    messages = conn.execute("SELECT * FROM messages ORDER BY created_at ASC LIMIT 5").fetchall()
    print("\n前5条消息:")
    for msg in messages:
        print(f"  ID: {msg['id']}, 发送者: {msg['sender_id']}, 接收者: {msg['receiver_id']}, 内容: {msg['content'][:30]}...")
    
    conn.close()

# 主测试函数
if __name__ == "__main__":
    print("=== 开始测试消息功能 ===")
    
    # 测试数据库结构
    test_users_table()
    test_messages_table()
    
    # 测试不同用户组合的消息查询
    print("\n=== 测试不同用户组合 ===")
    
    # 用户1和用户2之间的消息
    get_message_history(1, 2)
    
    # 用户2和用户3之间的消息（这应该有数据）
    get_message_history(2, 3)
    
    # 用户1和用户3之间的消息
    get_message_history(1, 3)
    
    print("\n=== 测试完成 ===")