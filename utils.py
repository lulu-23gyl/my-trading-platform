import streamlit as st
from language import t
import time
from messages import get_unread_message_count
import smtplib
import ssl
from email.message import EmailMessage
import random

# 显示成功消息
def show_success_message(message):
    """显示成功消息"""
    success = st.success(message)
    time.sleep(2)
    success.empty()

# 显示错误消息
def show_error_message(message):
    """显示错误消息"""
    error = st.error(message)
    time.sleep(2)
    error.empty()

# 页面导航
def page_navigation():
    st.sidebar.title(t('menu.title'))
    
    # 定义图标字典
    icons = {
        "search": "🔍",
        "messages": "💬",
        "publish": "➕",
        "my_products": "📦",
        "profile": "👤",
        "auth": "🔐"
    }
    
    # 根据登录状态显示不同菜单
    if st.session_state.get('user'):
        # 获取未读消息数量
        unread_count = get_unread_message_count(st.session_state.user['id'])
        message_label = f"{t('menu.messages')}{' (' + str(unread_count) + ')' if unread_count > 0 else ''}"
        
        pages = {
            t('menu.search'): "search",
            message_label: "messages",
            t('menu.publish'): "publish",
            t('menu.my_products'): "my_products",
            t('menu.profile'): "profile"
        }
    else:
        pages = {
            t('menu.search'): "search",
            t('menu.auth'): "auth"
        }
    
    # 添加自定义CSS样式
    st.sidebar.markdown("""
    <style>
    .nav-card-container {
        padding: 0;
        margin: 0;
    }
    .nav-card {
        padding: 12px;
        margin: 5px 0;
        border-radius: 8px;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 2px solid #f0f0f0;
    }
    .nav-card:hover {
        background-color: #f0f0f0;
        border-color: #0066cc;
        transform: translateY(-2px);
    }
    .nav-card-active {
        background-color: #0066cc;
        color: white;
        border-color: #0066cc;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 显示未登录提示信息
    if not st.session_state.get('user'):
        st.sidebar.info(t('auth.login_prompt'))
    
    # 使用columns创建响应式布局
    cols = st.sidebar.columns(2)
    selected = None
    
    for i, (label, page) in enumerate(pages.items()):
        # 从标签中提取页面类型以获取图标
        page_type = None
        for key, value in pages.items():
            if key == label or (value == "messages" and label.startswith(t('menu.messages'))):
                page_type = value
                break
        icon = icons.get(page_type, "📋")
        
        # 选择列
        col = cols[i % 2]
        
        # 检查是否为当前选中的页面
        is_active = st.session_state.get('selected_page') == page
        
        # 创建卡片按钮
        button_label = f"{icon} {label}"
        
        # 设置按钮样式
        button_kwargs = {
            "use_container_width": True,
            "type": "primary" if is_active else "secondary",
            "key": page
        }
        
        # 创建卡片
        if col.button(button_label, **button_kwargs):
            selected = page
            st.session_state['selected_page'] = page
    
    # 如果是首次加载，默认选择第一个页面
    if selected is None:
        if 'selected_page' not in st.session_state:
            st.session_state['selected_page'] = list(pages.values())[0]
        return st.session_state['selected_page']
    
    return selected


def generate_verification_code():
    """生成6位数字验证码"""
    return str(random.randint(100000, 999999))


def send_email(to_email, subject, body):
    """通过SMTP发送邮件，使用st.secrets['smtp']配置。
    支持端口 465 的 SSL 方式；若 465 被网络/防火墙阻断，自动回退到 587 + STARTTLS。
    需要配置示例：
    [smtp]
    host = "smtp.example.com"
    port = 465
    user = "no-reply@example.com"
    password = "your_password"
    from = "no-reply@example.com"
    """
    try:
        smtp_conf = st.secrets.get('smtp', {})
    except Exception:
        smtp_conf = {}
    host = smtp_conf.get('host')
    port = int(smtp_conf.get('port', 465))
    user = smtp_conf.get('user')
    password = smtp_conf.get('password')
    from_email = smtp_conf.get('from', user)

    if not all([host, port, user, password, from_email]):
        return False, t('auth.email_not_configured')

    # 构造邮件
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    msg.set_content(body)

    context = ssl.create_default_context()
    # 兼容性降级的 TLS 上下文（部分国内邮箱服务器或老旧中间设备可能导致握手异常/连接被关闭）
    low_context = ssl.create_default_context()
    try:
        low_context.set_ciphers('DEFAULT:@SECLEVEL=1')
    except Exception:
        pass

    def _attempt_send_ssl(use_context):
        # 使用 465 端口 SSL，若在退出阶段断开，也视为发送成功，避免重复发送
        server = None
        try:
            server = smtplib.SMTP_SSL(host, port, context=use_context, timeout=10)
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)
            try:
                server.quit()
            except Exception:
                # 退出阶段断开（常见于部分服务器/中间设备），邮件已发送，忽略
                pass
            return True
        except Exception as e:
            # 发送失败（在真正发送前或发送过程中异常）
            return False
        finally:
            if server:
                try:
                    server.close()
                except Exception:
                    pass

    def _attempt_send_starttls(target_port: int, use_context):
        # 使用 STARTTLS，若在退出阶段断开，也视为发送成功，避免重复发送
        server = None
        try:
            server = smtplib.SMTP(host, target_port, timeout=10)
            server.ehlo()
            server.starttls(context=use_context)
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)
            try:
                server.quit()
            except Exception:
                pass
            return True
        except Exception:
            return False
        finally:
            if server:
                try:
                    server.close()
                except Exception:
                    pass

    # 首选按端口策略发送；仅在“发送失败”时才回退，不会因退出阶段的断开重复发送
    if port == 465:
        if _attempt_send_ssl(context):
            return True, t('auth.email_sent')
        # SSL失败 → 尝试低安全级别
        if _attempt_send_ssl(low_context):
            return True, t('auth.email_sent')
        # 再尝试 587 STARTTLS
        if _attempt_send_starttls(587, context):
            return True, t('auth.email_sent')
        if _attempt_send_starttls(587, low_context):
            return True, t('auth.email_sent')
        return False, t('auth.email_send_failed').format('SSL/STARTTLS all attempts failed')
    elif port == 587:
        if _attempt_send_starttls(587, context):
            return True, t('auth.email_sent')
        if _attempt_send_starttls(587, low_context):
            return True, t('auth.email_sent')
        # 回退试试 SSL（少数服务器在 587 也支持直接 SSL）
        if _attempt_send_ssl(context):
            return True, t('auth.email_sent')
        if _attempt_send_ssl(low_context):
            return True, t('auth.email_sent')
        return False, t('auth.email_send_failed').format('STARTTLS/SSL all attempts failed')
    else:
        # 其他端口：先试 SSL，再试 STARTTLS（用同一端口），带低安全级别回退
        if _attempt_send_ssl(context):
            return True, t('auth.email_sent')
        if _attempt_send_ssl(low_context):
            return True, t('auth.email_sent')
        if _attempt_send_starttls(port, context):
            return True, t('auth.email_sent')
        if _attempt_send_starttls(port, low_context):
            return True, t('auth.email_sent')
        return False, t('auth.email_send_failed').format('All attempts failed')
