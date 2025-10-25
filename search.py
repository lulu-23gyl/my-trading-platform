import streamlit as st
import sqlite3
from database import get_db_connection
from messages import show_contact_seller_button
from language import t

# 创建反向映射，用于将数据库中的中文值映射到英文键名
def get_category_key(category_text):
    """根据分类文本获取对应的英文键名"""
    category_mapping = {
        "电子产品": "electronics",
        "家居用品": "household",
        "服装": "clothing",
        "图书": "books",
        "运动用品": "sports",
        "其他": "other"
    }
    return category_mapping.get(category_text, category_text)

def get_condition_key(condition_text):
    """根据新旧程度文本获取对应的英文键名"""
    condition_mapping = {
        "全新": "new",
        "几乎全新": "like_new",
        "轻微使用痕迹": "minor_wear",
        "正常使用": "normal",
        "使用较久": "heavy_wear"
    }
    return condition_mapping.get(condition_text, condition_text)

# 搜索商品
def search_products(keyword=None, category=None, min_price=None, max_price=None, sort_by="created_at"):
    conn = get_db_connection()
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND title LIKE ?"
        params.append(f"%{keyword}%")
    
    if category and category != t("search.all"):
        query += " AND category = ?"
        # 需要将当前语言的类别翻译回中文存储值
        reverse_category_mapping = {
            t('product.categories.electronics'): "电子产品",
            t('product.categories.household'): "家居用品",
            t('product.categories.clothing'): "服装",
            t('product.categories.books'): "图书",
            t('product.categories.sports'): "运动用品",
            t('product.categories.other'): "其他"
        }
        db_category = reverse_category_mapping.get(category, category)
        params.append(db_category)
    
    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)
    
    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)
    
    # 排序
    order_map = {
        t("search.sort_newest"): "created_at DESC",
        t("search.sort_price_low"): "price ASC",
        t("search.sort_price_high"): "price DESC"
    }
    query += f" ORDER BY {order_map.get(sort_by, 'created_at DESC')}"
    
    # 获取产品ID列表
    product_ids = [row['id'] for row in conn.execute(query, params).fetchall()]
    conn.close()
    
    # 使用get_product_details函数处理每个产品，以支持多语言描述
    from products import get_product_details
    products = []
    for product_id in product_ids:
        product = get_product_details(product_id)
        if product:
            products.append(product)
    
    return products

# 获取所有商品类别
def get_all_categories():
    conn = get_db_connection()
    categories = [row['category'] for row in conn.execute('SELECT DISTINCT category FROM products').fetchall()]
    conn.close()
    
    # 直接返回数据库中的类别，不进行翻译
    return [t("search.all")] + categories

# 搜索页面
def search_page():
    st.title(t("page_titles.search"))
    
    # 搜索条件
    col1, col2 = st.columns(2)
    with col1:
        keyword = st.text_input(t("search.search_bar"))
        category = st.selectbox(t("search.filter_category"), get_all_categories())
    
    with col2:
        price_range = st.slider(t("search.price_range"), 0.0, 10000.0, (0.0, 5000.0))
        sort_by = st.selectbox(t("search.sort_price"), 
                             [t("search.sort_newest"), 
                              t("search.sort_price_low"), 
                              t("search.sort_price_high")])
    
    if st.button(t("search.search_button")):
        products = search_products(
            keyword=keyword,
            category=category,
            min_price=price_range[0],
            max_price=price_range[1],
            sort_by=sort_by
        )
        
        display_search_results(products)
    else:
        # 默认显示最新商品
        products = search_products(sort_by=sort_by)
        display_search_results(products)

# 显示搜索结果
def display_search_results(products):
    if not products:
        st.info(t("search.no_results"))
        return
    
    # 检查是否有选中的商品详情需要显示
    if 'showing_detail' in st.session_state:
        # 当显示详情时，我们应该直接使用get_product_details获取最新的多语言产品数据
        from products import get_product_details
        product = get_product_details(st.session_state.showing_detail)
        if product:
            show_product_detail(product)
            # 添加返回按钮
            if st.button(t("search.back_to_list"), key="back_to_list"):
                del st.session_state.showing_detail
        return
    
    # 如果没有点击详情按钮，则显示商品列表
    st.subheader(f"{t('search.results_found')} {len(products)} {t('search.products')}")
    
    # 网格布局显示商品
    cols = st.columns(3)
    for i, product in enumerate(products):
        with cols[i % 3]:
            st.subheader(product['title'])
            # 将数据库中的中文类别转换为当前语言
            cat_key = get_category_key(product['category'])
            st.write(f"{t('product.category')}: {t(f'product.categories.{cat_key}')}")
            
            # 将数据库中的中文新旧程度转换为当前语言
            cond_key = get_condition_key(product['condition'])
            st.write(f"{t('product.condition')}: {t(f'product.conditions.{cond_key}')}")
            
            st.write(f"{t('product.price')}: ¥{product['price']}")
            
            # 显示商品详情按钮
            if st.button(t('search.view_details'), key=f"view_{product['id']}"):
                st.session_state.showing_detail = product['id']
                # 强制页面重新渲染，只显示详情
                st.rerun()

# 显示商品详情
def show_product_detail(product):
    st.title(product['title'])
    st.write(f"{t('product.created_at')}: {product['created_at']}")
    
    # 获取卖家信息
    conn = get_db_connection()
    seller = conn.execute("SELECT username FROM users WHERE id = ?", (product['user_id'],)).fetchone()
    conn.close()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader(t("product.info"))
        # 将数据库中的中文类别转换为当前语言
        cat_key = get_category_key(product['category'])
        st.write(f"{t('product.category')}: {t(f'product.categories.{cat_key}')}")
        
        # 将数据库中的中文新旧程度转换为当前语言
        cond_key = get_condition_key(product['condition'])
        st.write(f"{t('product.condition')}: {t(f'product.conditions.{cond_key}')}")
        st.write(f"{t('product.price')}: ¥{product['price']}")
        st.write(f"{t('product.seller')}: {seller['username']}" if seller else t("product.seller_info_unavailable"))
        
        # 显示联系卖家按钮
        show_contact_seller_button(product)
    
    with col2:
        st.subheader(t("product.description"))
        st.write(product['description'])
        
        # 如果有图片，显示图片
        if product['image_path']:
            import os
            if os.path.exists(product['image_path']):
                st.subheader(t("product.product_image"))
                st.image(product['image_path'])
            else:
                st.warning(t("product.image_not_found"))
    
    # 联系信息部分可以保留，但鼓励用户通过系统消息联系
    st.subheader(t("product.contact"))
    st.write(t("product.safe_transaction_message"))
    st.info(f"{t('product.contact_phone')}: {product['contact_info']}")
