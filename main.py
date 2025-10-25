import streamlit as st
from utils import page_navigation
from auth import auth_page
from products import product_publish_page, product_management_page
from search import search_page
from messages import messages_page
from language import get_language_selector, t, LANGUAGES

# 设置页面配置
st.set_page_config(
    page_title=f"{t('app_title')} - BLCU",
    page_icon="📦",
    layout="wide"
)

# 初始化会话状态
if 'page' not in st.session_state:
    st.session_state.page = 'search'

# 主应用
def main():
    # 显示语言选择器
    get_language_selector()
    
    # 使用翻译函数设置标题
    st.title(f"📦 {t('app_title')}")
    
    # 页面导航
    selected_page = page_navigation()
    
    # 根据选择的页面显示不同内容
    if selected_page == "search":
        search_page()
    elif selected_page == "auth":
        auth_page()
    elif selected_page == "publish":
        product_publish_page()
    elif selected_page == "my_products":
        product_management_page()
    elif selected_page == "profile":
        st.title(t('page_titles.profile'))
        if st.session_state.user:
            st.write(f"{t('profile.username')}: {st.session_state.user['username']}")
            st.write(f"{t('profile.email')}: {st.session_state.user['email']}")
            # 可以添加更多用户信息和设置选项
        else:
            st.warning(t('profile.login_required'))
    elif selected_page == "messages":
        messages_page()

if __name__ == "__main__":
    main()
