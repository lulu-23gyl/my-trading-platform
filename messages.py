import streamlit as st
import sqlite3
from database import get_db_connection
from datetime import datetime, timedelta
import time
import json
from language import t

# 安全的时间格式化函数
def safe_format_time(time_value):
    """处理各种时间格式并返回正确的格式化结果，确保使用本地时间"""
    if isinstance(time_value, str):
        # 尝试多种时间格式解析
        formats_to_try = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M"
        ]
        for fmt in formats_to_try:
            try:
                # 解析时间字符串为datetime对象
                dt = datetime.strptime(time_value, fmt)
                return dt
            except ValueError:
                continue
        # 如果都失败，返回当前时间
        return datetime.now()
    elif isinstance(time_value, datetime):
        # 直接返回datetime对象
        return time_value
    else:
        # 其他情况返回当前时间
        return datetime.now()

# 格式化消息显示时间
def format_message_time(dt):
    """根据消息时间与当前时间的关系，返回合适的显示格式"""
    now = datetime.now()
    dt = safe_format_time(dt)
    
    # 同一天显示时分
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    # 昨天显示"昨天 时分"
    elif dt.date() == (now - timedelta(days=1)).date():
        return f"昨天 {dt.strftime('%H:%M')}"
    # 今年显示"月-日 时分"
    elif dt.year == now.year:
        return dt.strftime("%m-%d %H:%M")
    # 其他情况显示完整日期时间
    else:
        return dt.strftime("%Y-%m-%d %H:%M")

# 格式化对话列表时间
def format_conversation_time(dt):
    """对话列表中的时间格式化"""
    now = datetime.now()
    dt = safe_format_time(dt)
    
    # 同一天显示时分
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    # 昨天显示"昨天"
    elif dt.date() == (now - timedelta(days=1)).date():
        return "昨天"
    # 今年显示"月-日"
    elif dt.year == now.year:
        return dt.strftime("%m-%d")
    # 其他情况显示完整日期
    else:
        return dt.strftime("%Y-%m-%d")

# 生成用户头像（使用用户名首字母或随机字符串）
def get_user_avatar(username):
    # 使用用户名的前两个字符作为头像文字，保证中文也能正确显示
    avatar_text = username[:2].upper()
    # 简单的颜色生成算法，基于用户名生成固定的背景色
    color_seed = sum(ord(c) for c in username) % 10
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7",
        "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E9"
    ]
    bg_color = colors[color_seed]
    return avatar_text, bg_color

# 发送消息
def send_message(sender_id, receiver_id, content, product_id=None):
    """发送新消息，使用本地时间并保存到数据库"""
    conn = get_db_connection()
    c = conn.cursor()
    # 获取当前本地时间，确保消息时间准确
    local_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """INSERT INTO messages (sender_id, receiver_id, content, product_id, created_at, is_read)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (sender_id, receiver_id, content, product_id, local_time, 0)  # 初始未读
    )
    conn.commit()
    conn.close()
    return True  # 返回True表示消息发送成功

# 获取用户的对话列表
def get_conversations(user_id):
    """获取用户的所有对话列表，包含未读消息数和最后一条消息"""
    conn = get_db_connection()
    
    # 获取与该用户相关的所有对话，按照最后一条消息的时间排序
    query = """
    SELECT 
        CASE 
            WHEN sender_id = ? THEN receiver_id 
            ELSE sender_id 
        END as other_user_id,
        MAX(created_at) as last_message_time,
        COUNT(CASE WHEN receiver_id = ? AND is_read = 0 THEN 1 END) as unread_count
    FROM messages
    WHERE sender_id = ? OR receiver_id = ?
    GROUP BY other_user_id
    ORDER BY last_message_time DESC
    """
    conversations = conn.execute(query, (user_id, user_id, user_id, user_id)).fetchall()
    
    # 获取每个对话中对方用户的信息
    result = []
    for conv in conversations:
        other_user_id = conv['other_user_id']
        # 获取对方用户信息
        user_info = conn.execute("SELECT username, email FROM users WHERE id = ?", (other_user_id,)).fetchone()
        if user_info:
            # 获取最后一条消息内容
            last_message_query = """
            SELECT content, sender_id FROM messages 
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY created_at DESC LIMIT 1
            """
            last_msg = conn.execute(last_message_query, 
                                  (user_id, other_user_id, other_user_id, user_id)).fetchone()
            
            # 格式化时间
            formatted_time = format_conversation_time(conv['last_message_time'])
            
            # 构建消息预览
            last_message_preview = ""
            if last_msg:
                # 判断是否是自己发的消息
                is_self_sent = last_msg['sender_id'] == user_id
                prefix = "我: " if is_self_sent else ""
                content = last_msg['content']
                last_message_preview = prefix + (content[:20] + '...' if len(content) > 20 else content)
            
            result.append({
                'user_id': other_user_id,
                'username': user_info['username'],
                'last_message_time': formatted_time,
                'unread_count': conv['unread_count'],
                'last_message': last_message_preview
            })
    
    conn.close()
    return result

# 获取两个用户之间的消息历史
def get_message_history(user_id1, user_id2, product_id=None):
    """获取两个用户之间的消息历史，标记消息为已读"""
    conn = get_db_connection()
    
    # 构建基础查询
    query = """
    SELECT m.*, u.username as sender_name 
    FROM messages m
    JOIN users u ON m.sender_id = u.id
    WHERE 
        (m.sender_id = ? AND m.receiver_id = ?) OR 
        (m.sender_id = ? AND m.receiver_id = ?)
    """
    params = [user_id1, user_id2, user_id2, user_id1]
    
    # 如果指定了商品ID，则只获取与该商品相关的消息
    if product_id:
        query += " AND m.product_id = ?"
        params.append(product_id)
    
    # 按时间正序排列，确保消息按发送顺序显示
    query += " ORDER BY m.created_at ASC"
    
    # 执行查询获取消息
    messages = conn.execute(query, params).fetchall()
    
    # 将接收方为当前用户的消息标记为已读
    conn.execute(
        "UPDATE messages SET is_read = 1 WHERE receiver_id = ? AND sender_id = ?",
        (user_id1, user_id2)
    )
    conn.commit()
    conn.close()
    return messages

# 删除单条消息
def delete_message(message_id, user_id):
    """删除指定ID的消息，确保只能删除自己发送或接收的消息"""
    conn = get_db_connection()
    
    try:
        # 首先检查消息是否存在且属于当前用户
        message = conn.execute(
            "SELECT * FROM messages WHERE id = ? AND (sender_id = ? OR receiver_id = ?)",
            (message_id, user_id, user_id)
        ).fetchone()
        
        if not message:
            return False, "消息不存在或无权删除"
        
        # 删除消息
        conn.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        conn.commit()
        return True, "消息删除成功"
    except Exception as e:
        conn.rollback()
        return False, f"删除失败: {str(e)}"
    finally:
        conn.close()

# 清空两个用户之间的聊天历史
def clear_conversation_history(user_id1, user_id2):
    """清空两个用户之间的所有聊天记录"""
    conn = get_db_connection()
    
    try:
        # 删除两个用户之间的所有消息
        conn.execute(
            "DELETE FROM messages WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)",
            (user_id1, user_id2, user_id2, user_id1)
        )
        conn.commit()
        return True, "聊天历史已清空"
    except Exception as e:
        conn.rollback()
        return False, f"清空失败: {str(e)}"
    finally:
        conn.close()

# 获取用户信息（根据ID）
def get_user_info(user_id):
    """根据用户ID获取用户详细信息"""
    conn = get_db_connection()
    user = conn.execute("SELECT id, username, email FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

# 按日期分组消息
def group_messages_by_date(messages):
    """将消息按日期分组，用于显示"""
    grouped = {}
    
    for msg in messages:
        # 确保消息有created_at字段并转换为日期
        created_at = safe_format_time(msg['created_at'])
        date_key = created_at.date().isoformat()
        
        if date_key not in grouped:
            grouped[date_key] = []
        grouped[date_key].append(msg)
    
    # 按日期排序（升序）
    return dict(sorted(grouped.items()))

# 格式化日期显示
def format_date_header(date_str):
    """格式化日期显示为'今天'、'昨天'或具体日期"""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    if date_obj == today:
        return "今天"
    elif date_obj == yesterday:
        return "昨天"
    else:
        return date_obj.strftime("%Y年%m月%d日")

# 聊天页面主函数
def messages_page():
    """完整的聊天功能页面，包含联系人列表和消息对话"""
    # 检查用户登录状态
    if 'user' not in st.session_state or not st.session_state.user:
        st.warning(t('auth.login_required'))
        return
    
    # 初始化会话状态
    if 'selected_conversation' not in st.session_state:
        st.session_state.selected_conversation = None
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    if 'show_chat_settings' not in st.session_state:
        st.session_state.show_chat_settings = False
    if 'confirming_clear' not in st.session_state:
        st.session_state.confirming_clear = False
    
    # 添加自定义CSS
    st.markdown("""
    <style>
    /* 全局样式重置 */
    * {
        box-sizing: border-box;
    }
    
    /* 聊天容器样式 */
    .chat-container {
        height: calc(100vh - 200px);
        display: flex;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* 响应式调整 */
    @media (max-width: 768px) {
        .chat-container {
            flex-direction: column;
            height: calc(100vh - 180px);
        }
        .conversation-list {
            width: 100% !important;
            height: 30% !important;
            border-right: none !important;
            border-bottom: 1px solid #e0e0e0;
        }
        .chat-area {
            width: 100% !important;
            height: 70% !important;
        }
    }
    
    /* 左侧对话列表样式 */
    .conversation-list {
        width: 300px;
        background-color: #fff;
        border-right: 1px solid #e0e0e0;
        overflow-y: auto;
    }
    
    .conversation-item {
        padding: 12px 16px;
        border-bottom: 1px solid #f0f0f0;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    
    .conversation-item:hover {
        background-color: #f8f9fa;
    }
    
    .conversation-item-active {
        background-color: #e3f2fd;
    }
    
    .conversation-item-content {
        display: flex;
        align-items: center;
    }
    
    /* 头像样式 */
    .avatar {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 16px;
        margin-right: 12px;
        flex-shrink: 0;
    }
    
    /* 未读消息徽章 */
    .unread-badge {
        background-color: #ff4757;
        color: white;
        border-radius: 50%;
        min-width: 20px;
        height: 20px;
        font-size: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 6px;
        flex-shrink: 0;
    }
    
    /* 消息预览区域 */
    .message-preview {
        flex: 1;
        min-width: 0;
    }
    
    .message-preview-username {
        font-weight: 600;
        font-size: 14px;
        margin-bottom: 4px;
        color: #333;
    }
    
    .message-preview-text {
        font-size: 13px;
        color: #666;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .time-badge-container {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
        margin-left: 8px;
        min-width: 60px;
    }
    
    .time-badge {
        font-size: 12px;
        color: #999;
        margin-bottom: 4px;
    }
    
    /* 右侧聊天区域样式 */
    .chat-area {
        flex: 1;
        display: flex;
        flex-direction: column;
        background-color: #f5f5f5;
    }
    
    /* 聊天头部 */
    .chat-header {
        padding: 12px 20px;
        background-color: #fff;
        border-bottom: 1px solid #e0e0e0;
        display: flex;
        align-items: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    .chat-header-info {
        margin-left: 12px;
    }
    
    .chat-header-username {
        font-weight: 600;
        font-size: 16px;
        color: #333;
    }
    
    /* 消息容器 */
    .messages-container {
        flex: 1;
        padding: 20px;
        overflow-y: auto;
        background-color: #f8f9fa;
        background-image: url('data:image/svg+xml;charset=utf-8,%3Csvg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"%3E%3Cpath d="M11 18c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm48 25c3.866 0 7-3.134 7-7s-3.134-7-7-7-7 3.134-7 7 3.134 7 7 7zm-43-7c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm63 31c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM34 90c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zm56-76c1.657 0 3-1.343 3-3s-1.343-3-3-3-3 1.343-3 3 1.343 3 3 3zM12 86c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm28-65c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm23-11c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-6 60c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm29 22c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zM32 63c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm57-13c2.76 0 5-2.24 5-5s-2.24-5-5-5-5 2.24-5 5 2.24 5 5 5zm-9-21c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM60 91c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM35 41c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2zM12 60c1.105 0 2-.895 2-2s-.895-2-2-2-2 .895-2 2 .895 2 2 2z" fill="%23e9ecef" fill-opacity="0.4" fill-rule="evenodd"/%3E%3C/svg%3E');
    }
    
    /* 日期分隔线 */
    .date-divider {
        text-align: center;
        margin: 20px 0;
    }
    
    .date-divider span {
        background-color: rgba(0,0,0,0.1);
        color: #666;
        padding: 4px 12px;
        border-radius: 10px;
        font-size: 12px;
    }
    
    /* 消息行 */
    .message-row {
        display: flex;
        margin-bottom: 16px;
        align-items: flex-end;
    }
    
    .message-row-sender {
        justify-content: flex-end;
    }
    
    .message-row-receiver {
        justify-content: flex-start;
    }
    
    /* 消息内容 */
    .message-content {
        max-width: 70%;
        position: relative;
    }
    
    /* 消息气泡 */
    .message-bubble {
        padding: 10px 15px;
        border-radius: 18px;
        word-wrap: break-word;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .message-bubble-sender {
        background-color: #95ec69;
        border-bottom-right-radius: 4px;
    }
    
    .message-bubble-receiver {
        background-color: #fff;
        border-bottom-left-radius: 4px;
        color: #000;
    }
    
    /* 消息时间 */
    .message-time {
        font-size: 12px;
        color: #999;
        margin-top: 4px;
    }
    
    /* 接收方消息带头像 */
    .message-receiver-avatar {
        margin-right: 8px;
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: 14px;
        flex-shrink: 0;
    }
    
    /* 输入区域 */
    .input-area {
        padding: 16px;
        background-color: #fff;
        border-top: 1px solid #e0e0e0;
        box-shadow: 0 -1px 3px rgba(0,0,0,0.05);
    }
    
    /* 消息输入框 */
    .message-input {
        width: 100%;
        border: 1px solid #e0e0e0;
        border-radius: 20px;
        padding: 10px 15px;
        resize: none;
        font-family: inherit;
        font-size: 14px;
        transition: border-color 0.3s;
    }
    
    .message-input:focus {
        outline: none;
        border-color: #0078d4;
        box-shadow: 0 0 0 2px rgba(0,120,212,0.1);
    }
    
    /* 发送按钮 */
    .send-button {
        background-color: #0078d4;
        color: white;
        border: none;
        border-radius: 20px;
        padding: 10px 20px;
        cursor: pointer;
        font-weight: 500;
        transition: background-color 0.3s;
    }
    
    .send-button:hover {
        background-color: #005a9e;
    }
    
    .send-button:disabled {
        background-color: #cccccc;
        cursor: not-allowed;
    }
    
    /* 空状态 */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 100%;
        color: #999;
        text-align: center;
    }
    
    .empty-state-icon {
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
    }
    
    .empty-state-text {
        font-size: 16px;
    }
    
    /* 无对话状态 */
    .no-conversations {
        text-align: center;
        padding: 40px 20px;
        color: #666;
    }
    
    /* 刷新按钮 */
    .refresh-button {
        background-color: transparent;
        border: 1px solid #e0e0e0;
        border-radius: 4px;
        padding: 6px 12px;
        cursor: pointer;
        font-size: 14px;
        margin-top: 10px;
        transition: background-color 0.3s;
    }
    
    .refresh-button:hover {
        background-color: #f5f5f5;
    }
    </style>
    """, unsafe_allow_html=True)
    
    st.title(f"📬 {t('page_titles.messages')}")
    
    # 创建聊天容器
    col1, col2 = st.columns([1, 2])
    
    # 左侧对话列表
    with col1:
        st.markdown("<div class='conversation-list'>", unsafe_allow_html=True)
        
        # 获取对话列表
        conversations = get_conversations(st.session_state.user['id'])
        
        if not conversations:
            # 无对话状态
            st.markdown(f"""
            <div class='no-conversations'>
                <div class='empty-state-icon'>💬</div>
                <div>{t('messages.no_conversations')}</div>
                <div style='font-size: 14px; margin-top: 8px;'>{t('messages.start_chat_prompt')}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # 显示对话列表
            for conv in conversations:
                avatar_text, bg_color = get_user_avatar(conv['username'])
                is_active = st.session_state.selected_conversation == conv['user_id']
                
                # 构建对话项的CSS类
                conversation_classes = "conversation-item"
                if is_active:
                    conversation_classes += " conversation-item-active"
                
                # 显示对话项
                with st.container():
                    st.markdown(f"<div class='{conversation_classes} conversation-item-content'>", unsafe_allow_html=True)
                    
                    # 头像
                    st.markdown(f"<div class='avatar' style='background-color: {bg_color};'>{avatar_text}</div>", unsafe_allow_html=True)
                    
                    # 消息预览
                    display_preview = conv['last_message']
                    
                    st.markdown(f"""
                    <div class='message-preview'>
                        <div class='message-preview-username'>{conv['username']}</div>
                        <div class='message-preview-text'>{display_preview}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 时间和未读标记
                    st.markdown(f"<div class='time-badge-container'>", unsafe_allow_html=True)
                    st.markdown(f"<div class='time-badge'>{conv['last_message_time']}</div>", unsafe_allow_html=True)
                    if conv['unread_count'] > 0:
                        st.markdown(f"<div class='unread-badge'>{conv['unread_count']}</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    st.markdown("</div>", unsafe_allow_html=True)
                
                # 使用隐藏的按钮来处理点击事件
                if st.button(
                    conv['username'],  # 按钮文本，但会被上面的内容覆盖
                    key=f"conv_{conv['user_id']}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                    help="点击打开对话",
                    on_click=lambda uid=conv['user_id']: setattr(st.session_state, 'selected_conversation', uid)
                ):
                    st.session_state.selected_conversation = conv['user_id']
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # 右侧聊天区域
    with col2:
        st.markdown("<div class='chat-area'>", unsafe_allow_html=True)
        
        if st.session_state.selected_conversation:
            # 获取对方用户信息
            other_user_info = get_user_info(st.session_state.selected_conversation)
            
            if other_user_info:
                # 聊天头部
                avatar_text, bg_color = get_user_avatar(other_user_info['username'])
                
                # 创建聊天头部容器
                header_container = st.container()
                with header_container:
                    # 显示用户信息
                    st.markdown(f"""
                    <div class='chat-header'>
                        <div class='avatar' style='background-color: {bg_color};'>{avatar_text}</div>
                        <div class='chat-header-info'>
                            <div class='chat-header-username'>{other_user_info['username']}</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 添加设置菜单按钮，将清空聊天功能移到设置菜单
                    col_actions = st.columns([1, 1])
                    with col_actions[1]:
                        if st.button(
                            "⚙️ " + t("messages.chat_settings"),
                            key="chat_settings",
                            type="secondary",
                            use_container_width=True,
                            help=t("messages.chat_settings_help")
                        ):
                            # 切换设置菜单显示状态
                            st.session_state.show_chat_settings = not st.session_state.show_chat_settings
                
                # 显示聊天设置菜单（如果开启）
                if st.session_state.show_chat_settings:
                    with st.expander(t("messages.chat_settings"), expanded=True):
                        st.warning(t("messages.operation_irreversible"))
                        
                        # 根据确认状态显示不同按钮
                        if not st.session_state.confirming_clear:
                            # 第一步：显示清空聊天记录按钮
                            if st.button(
                                "🗑️ " + t("messages.clear_chat_history"),
                                key="clear_history_danger",
                                type="secondary",
                                use_container_width=True,
                                help=t("messages.clear_history_help")
                            ):
                                # 设置确认状态
                                st.session_state.confirming_clear = True
                        else:
                            # 第二步：显示确认和取消按钮
                            st.warning("⚠️ " + t("messages.confirm_clear_history"))
                            col_confirm = st.columns([1, 1])
                            with col_confirm[0]:
                                if st.button(
                                    t("messages.confirm"),
                                    key="confirm_clear_history",
                                    type="primary"
                                ):
                                    if st.session_state.user['id'] and st.session_state.selected_conversation:
                                        # 添加详细日志
                                        print(f"开始清空聊天记录 - 用户ID: {st.session_state.user['id']}, 对方ID: {st.session_state.selected_conversation}")
                                        
                                        # 执行清空操作
                                        success, message = clear_conversation_history(
                                            st.session_state.user['id'],
                                            st.session_state.selected_conversation
                                        )
                                        
                                        # 记录操作结果
                                        print(f"清空聊天记录结果 - 成功: {success}, 消息: {message}")
                                        
                                        if success:
                                            # 重置状态
                                            st.session_state.confirming_clear = False
                                            st.session_state.show_chat_settings = False
                                            # 显示成功消息
                                            st.success(message)
                                        else:
                                            st.error(message)
                            
                            with col_confirm[1]:
                                if st.button(
                                    t("messages.cancel"),
                                    key="cancel_clear_history",
                                    type="secondary"
                                ):
                                    # 取消操作，重置状态
                                    st.session_state.confirming_clear = False
                
                # 获取消息历史
                messages = []
                try:
                    messages = get_message_history(
                        st.session_state.user['id'], 
                        st.session_state.selected_conversation
                    )
                    # 添加日志以便调试
                    print(f"成功获取到 {len(messages)} 条消息")
                except Exception as e:
                    st.error(f"获取消息历史失败: {str(e)}")
                    print(f"获取消息历史错误: {str(e)}")
                
                # 显示消息内容
                st.markdown("<div class='messages-container'>", unsafe_allow_html=True)
                
                if not messages:
                    # 空消息状态
                    st.markdown(f"""
                    <div class='empty-state'>
                        <div class='empty-state-icon'>💬</div>
                        <div class='empty-state-text'>{t('messages.start_conversation')}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # 按日期分组显示消息
                    grouped_messages = group_messages_by_date(messages)
                    
                    # 遍历每个日期组
                    for date_key, date_messages in grouped_messages.items():
                        # 显示日期分隔线
                        st.markdown(f"""
                        <div class='date-divider'>
                            <span>{format_date_header(date_key)}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 添加右键菜单相关代码
                        st.markdown("""
                        <style>
                        /* 右键菜单样式 */
                        .context-menu {
                            position: fixed;
                            display: none;
                            background-color: white;
                            border: 1px solid #ccc;
                            border-radius: 6px;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                            z-index: 1000;
                            min-width: 150px;
                        }
                        .context-menu-item {
                            padding: 8px 16px;
                            cursor: pointer;
                            user-select: none;
                        }
                        .context-menu-item:hover {
                            background-color: #f0f0f0;
                        }
                        /* 消息容器右键提示 */
                        .message-container {
                            cursor: pointer;
                        }
                        /* 防止默认右键菜单 */
                        .message-container {
                            -webkit-user-select: none;
                            -moz-user-select: none;
                            -ms-user-select: none;
                            user-select: none;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("""
                        <div id="contextMenu" class="context-menu">
                            <div id="deleteOption" class="context-menu-item">🗑️ 删除消息</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("""
                        <script>
                        // 获取右键菜单元素
                        const contextMenu = document.getElementById('contextMenu');
                        const deleteOption = document.getElementById('deleteOption');
                        let currentMessageId = null;
                        
                        // 显示右键菜单的函数
                        function showContextMenu(event, messageId) {
                            event.preventDefault();
                            
                            // 保存当前消息ID
                            currentMessageId = messageId;
                            
                            // 设置菜单位置
                            contextMenu.style.left = event.pageX + 'px';
                            contextMenu.style.top = event.pageY + 'px';
                            contextMenu.style.display = 'block';
                        }
                        
                        // 隐藏右键菜单
                        function hideContextMenu() {
                            contextMenu.style.display = 'none';
                        }
                        
                        // 点击删除选项
                        deleteOption.addEventListener('click', function() {
                            if (currentMessageId) {
                                // 使用Streamlit的方式触发删除操作
                                const btnId = 'delete_btn_' + currentMessageId;
                                const btn = document.getElementById(btnId);
                                if (btn) {
                                    btn.click();
                                }
                                hideContextMenu();
                            }
                        });
                        
                        // 点击页面其他地方隐藏菜单
                        document.addEventListener('click', hideContextMenu);
                        
                        // 初始化所有消息的右键事件
                        document.querySelectorAll('.message-container').forEach(function(element) {
                            element.addEventListener('contextmenu', function(e) {
                                const messageId = this.getAttribute('data-message-id');
                                showContextMenu(e, messageId);
                            });
                        });
                        </script>
                        """, unsafe_allow_html=True)
                        
                        # 显示该日期的所有消息
                        for msg in date_messages:
                            # 判断是否是当前用户发送的消息
                            is_sender = msg['sender_id'] == st.session_state.user['id']
                            
                            # 为每条消息创建一个容器
                            message_container = st.container()
                            with message_container:
                                if is_sender:
                                    # 发送者消息（右对齐）
                                    st.markdown(f"""
                                    <div class='message-container' data-message-id="{msg['id']}">
                                    <div class='message-row message-row-sender'>
                                        <div class='message-content'>
                                            <div class='message-bubble message-bubble-sender'>{msg['content']}</div>
                                            <div class='message-time' style='text-align: right;'>{format_message_time(msg['created_at'])}</div>
                                        </div>
                                    </div>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    # 接收者消息（左对齐，带头像）
                                    sender_avatar_text, sender_bg_color = get_user_avatar(msg['sender_name'])
                                    
                                    # 构建消息HTML
                                    message_html = f"""
                                    <div class='message-container' data-message-id="{msg['id']}">
                                    <div class='message-row message-row-receiver'>
                                        <div class='message-receiver-avatar' style='background-color: {sender_bg_color};'>{sender_avatar_text}</div>
                                        <div class='message-content'>
                                            <div class='message-bubble message-bubble-receiver'>{msg['content']}</div>
                                            <div class='message-time'>{format_message_time(msg['created_at'])}</div>
                                        </div>
                                    </div>
                                    </div>
                                    """
                                    
                                    # 显示消息
                                    st.markdown(message_html, unsafe_allow_html=True)
                                
                                # 添加隐藏的删除按钮，供JavaScript调用
                                st.button(
                                    "删除",
                                    key=f"delete_btn_{msg['id']}",
                                    type="secondary",
                                    help="删除这条消息",
                                    use_container_width=False,
                                    on_click=lambda msg_id=msg['id']: delete_message_action(msg_id)
                                )
                                
                                # 隐藏按钮的CSS
                                st.markdown(f"""
                                <style>
                                [data-testid="stButton"] > button[key="delete_btn_{msg['id']}"] {{
                                    display: none;
                                }}
                                </style>
                                """, unsafe_allow_html=True)
                        
                        # 删除消息的函数
                        def delete_message_action(message_id):
                            success, message = delete_message(message_id, st.session_state.user['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                # 关闭消息容器
                st.markdown("</div>", unsafe_allow_html=True)
                
                # 输入区域
                st.markdown("<div class='input-area'>", unsafe_allow_html=True)
                
                # 修改表单处理方式，使用Streamlit更可靠的表单处理
                with st.form("message_form", clear_on_submit=True):
                    # 调整列宽比例，确保按钮有足够空间
                    col1, col2 = st.columns([9, 1])
                    with col1:
                        message_content = st.text_area(
                            t('messages.input_label'), 
                            height=80, 
                            key="message_input", 
                            placeholder=t('messages.input_placeholder'), 
                            label_visibility="collapsed"
                        )
                    with col2:
                        st.markdown("", unsafe_allow_html=True)  # 占位，使按钮垂直居中
                        submit = st.form_submit_button(
                            t('messages.send_button'), 
                            use_container_width=True,
                            type="primary"
                        )
                
                # 添加调试信息区域
                debug_info = st.empty()
                
                # 使用更可靠的方式处理消息发送
                if submit and message_content.strip():
                    try:
                        debug_info.info("正在发送消息...")
                        # 发送消息
                        success = send_message(
                            st.session_state.user['id'],
                            st.session_state.selected_conversation,
                            message_content.strip()
                        )
                        if success:
                            debug_info.success(t('messages.send_success'))
                            # 为了确保消息显示，使用强制刷新
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            debug_info.error(t('messages.send_error'))
                    except Exception as e:
                        debug_info.error(f"{t('messages.send_error')}: {str(e)}")
                        print(f"消息发送错误: {str(e)}")
                
                # 提供手动刷新按钮
                col_refresh = st.columns([1])
                with col_refresh[0]:
                    if st.button(f"🔄 {t('messages.refresh')}", key="manual_refresh", help=t('messages.refresh_help'), use_container_width=True):
                        st.rerun()
                
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            # 未选择对话状态
            st.markdown(f"""
            <div class='empty-state'>
                <div class='empty-state-icon'>👥</div>
                <div class='empty-state-text'>{t('messages.select_contact_first')}</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

# 在商品详情页中显示联系卖家按钮
def show_contact_seller_button(product):
    """在商品详情页显示联系卖家按钮"""
    if 'user' not in st.session_state or not st.session_state.user:
        st.warning(t('auth.login_required'))
        return
    
    # 检查当前用户是否为商品卖家
    if st.session_state.user['id'] == product['user_id']:
        st.info(t('messages.cannot_contact_self'))
        return
    # 点击联系卖家按钮
    if st.button(f"💬 {t('product.contact_seller')}", key="contact_seller", type="primary", use_container_width=True):
        # 设置会话状态，跳转到消息页面并打开与卖家的对话
        st.session_state.selected_conversation = product['user_id']
        st.session_state['selected_page'] = 'messages'
        st.rerun()  # 立即跳转到消息页面

# 获取未读消息数量
def get_unread_message_count(user_id):
    """获取用户的未读消息总数"""
    conn = get_db_connection()
    count = conn.execute(
        "SELECT COUNT(*) as unread_count FROM messages WHERE receiver_id = ? AND is_read = 0",
        (user_id,)
    ).fetchone()['unread_count']
    conn.close()
    return count