import streamlit as st
import hashlib
import sqlite3
from datetime import datetime, timedelta
from database import get_db_connection
from language import t
from utils import generate_verification_code, send_email

# 密码加密
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 用户注册
def register_user(username, email, password):
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute(
            'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
            (username, email, hash_password(password))
        )
        conn.commit()
        return True, t('auth.register_success')
    except sqlite3.IntegrityError:
        return False, t('auth.username_email_exists')
    finally:
        conn.close()

# 用户登录
def login_user(username, password):
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    
    if user and user['password'] == hash_password(password):
        return True, user
    return False, t('auth.login_failed')

# 认证页面
def auth_page():
    st.title(t('page_titles.auth'))
    
    # 使用会话状态管理登录状态
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    # 登录/注册/找回密码 选项卡
    tab1, tab2, tab3 = st.tabs([t('auth.login'), t('auth.register'), t('auth.reset_password')])
    
    with tab1:
        if st.session_state.user:
            st.success(f"{t('auth.logged_in')}：{st.session_state.user['username']}")
            if st.button(t('auth.logout')):
                st.session_state.user = None
                st.rerun()
        else:
            username = st.text_input(t('auth.username'), key="login_username")
            password = st.text_input(t('auth.password'), type="password", key="login_password")
            
            if st.button(t('auth.login_button')):
                if not username or not password:
                    st.error(t('auth.enter_username_password'))
                else:
                    success, result = login_user(username, password)
                    if success:
                        st.session_state.user = result
                        st.session_state['selected_page'] = 'search'
                        st.success(t('auth.login_success'))
                        st.rerun()
                    else:
                        st.error(result)
    
    with tab2:
        new_username = st.text_input(t('auth.username'), key="reg_username")
        new_email = st.text_input(t('auth.email'), key="reg_email")
        new_password = st.text_input(t('auth.password'), type="password", key="reg_password")
        confirm_password = st.text_input(t('auth.confirm_password'), type="password", key="reg_confirm")
        
        if st.button(t('auth.register_button')):
            if not all([new_username, new_email, new_password, confirm_password]):
                st.error(t('auth.fill_all_fields'))
            elif new_password != confirm_password:
                st.error(t('auth.password_mismatch'))
            else:
                success, message = register_user(new_username, new_email, new_password)
                if success:
                    st.success(message)
                    st.info(t('auth.please_login'))
                else:
                    st.error(message)
    
    with tab3:
        # 邮箱输入
        reset_email = st.text_input(t('auth.email'), key="reset_email")

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button(t('auth.send_code'), key="send_reset_code"):
                if not reset_email:
                    st.error(t('auth.fill_all_fields'))
                else:
                    # 检查邮箱是否存在
                    conn = get_db_connection()
                    user = conn.execute('SELECT * FROM users WHERE email = ?', (reset_email,)).fetchone()
                    if not user:
                        st.error(t('auth.user_not_found_by_email'))
                        conn.close()
                    else:
                        # 生成验证码并保存到数据库
                        code = generate_verification_code()
                        expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()
                        conn.execute(
                            'INSERT INTO password_resets (email, code, expires_at, used) VALUES (?, ?, ?, 0)',
                            (reset_email, code, expires_at)
                        )
                        conn.commit()
                        conn.close()

                        # 发送邮件
                        subject = f"{t('auth.reset_password')}"
                        body = f"{t('auth.verification_code')}: {code}\n{t('auth.reset_password')}"
                        success, msg = send_email(reset_email, subject, body)
                        if success:
                            st.success(t('auth.email_sent'))
                        else:
                            st.warning(msg)
                            # 开发模式：显示验证码（当邮件未配置时）
                            st.info(f"{t('auth.verification_code')}: {code}")
        with col2:
            st.write("")

        # 输入验证码和新密码
        input_code = st.text_input(t('auth.verification_code'), key="input_reset_code")
        new_password = st.text_input(t('auth.new_password'), type="password", key="input_new_password")
        confirm_password = st.text_input(t('auth.confirm_password'), type="password", key="input_confirm_password")

        if st.button(t('auth.reset_password_button'), key="do_reset_password"):
            if not all([reset_email, input_code, new_password, confirm_password]):
                st.error(t('auth.fill_all_fields'))
            elif new_password != confirm_password:
                st.error(t('auth.password_mismatch'))
            else:
                conn = get_db_connection()
                record = conn.execute(
                    'SELECT * FROM password_resets WHERE email = ? AND used = 0 ORDER BY created_at DESC LIMIT 1',
                    (reset_email,)
                ).fetchone()

                if not record:
                    st.error(t('auth.code_invalid'))
                    conn.close()
                else:
                    # 验证码匹配与过期检查
                    now = datetime.now()
                    try:
                        exp = datetime.fromisoformat(record['expires_at'])
                    except Exception:
                        # 兼容非ISO格式（如果存在）
                        exp = now
                    if record['code'] != input_code:
                        st.error(t('auth.code_invalid'))
                        conn.close()
                    elif now > exp:
                        st.error(t('auth.code_expired'))
                        conn.close()
                    else:
                        # 更新用户密码
                        conn.execute(
                            'UPDATE users SET password = ? WHERE email = ?',
                            (hash_password(new_password), reset_email)
                        )
                        # 标记记录为已使用
                        conn.execute(
                            'UPDATE password_resets SET used = 1 WHERE id = ?',
                            (record['id'],)
                        )
                        conn.commit()
                        conn.close()
                        st.success(t('auth.reset_success'))
                        st.info(t('auth.please_login'))
