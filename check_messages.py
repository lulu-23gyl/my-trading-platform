import sqlite3

# 连接到数据库
conn = sqlite3.connect('second_hand_market.db')
conn.row_factory = sqlite3.Row  # 允许通过列名访问
cursor = conn.cursor()

print("检查数据库结构：")
# 检查messages表是否存在
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
table_exists = cursor.fetchone()
print(f"Messages表存在: {table_exists is not None}")

# 检查表结构
if table_exists:
    print("\nMessages表结构：")
    cursor.execute("PRAGMA table_info(messages)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"{col['name']}: {col['type']}")
    
    # 检查消息数据
    print("\nMessages表中的数据：")
    cursor.execute("SELECT * FROM messages LIMIT 10")
    messages = cursor.fetchall()
    print(f"消息总数: {len(messages)}")
    
    if messages:
        print("\n前3条消息内容：")
        for i, msg in enumerate(messages[:3]):
            print(f"\n消息 {i+1}:")
            for key in msg.keys():
                print(f"  {key}: {msg[key]}")
    
    # 检查用户表和消息关联
    print("\n检查用户表：")
    cursor.execute("SELECT * FROM users LIMIT 5")
    users = cursor.fetchall()
    print(f"用户总数: {len(users)}")
    
    if users:
        print("\n用户ID列表:")
        for user in users:
            print(f"  ID: {user['id']}, 用户名: {user['username']}")
        
        # 测试get_message_history类似的查询
        print("\n测试消息查询（基于前两个用户）:")
        if len(users) >= 2:
            user1_id = users[0]['id']
            user2_id = users[1]['id']
            print(f"查询用户 {user1_id} 和 {user2_id} 之间的消息:")
            cursor.execute("""
                SELECT m.*, u.username as sender_name 
                FROM messages m
                JOIN users u ON m.sender_id = u.id
                WHERE 
                    (m.sender_id = ? AND m.receiver_id = ?) OR 
                    (m.sender_id = ? AND m.receiver_id = ?)
                ORDER BY m.created_at ASC
            """, (user1_id, user2_id, user2_id, user1_id))
            test_messages = cursor.fetchall()
            print(f"找到 {len(test_messages)} 条消息")

# 关闭连接
conn.close()