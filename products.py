import streamlit as st
from database import get_db_connection
from datetime import datetime
from language import t
from search import get_category_key, get_condition_key

# 发布商品
def publish_product(user_id, title, description, price, category, condition, contact_info, image_path=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute(
            '''INSERT INTO products 
               (user_id, title, description, price, category, condition, contact_info, image_path, created_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, title, description, price, category, condition, contact_info, image_path, datetime.now())
        )
        conn.commit()
        return True, t('product.publish_success')
    except Exception as e:
        return False, f"{t('product.publish_failed')}: {str(e)}"
    finally:
        conn.close()

# 获取用户发布的商品
def get_user_products(user_id):
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    conn.close()
    return products

# 获取商品详情
def get_product_details(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    return product

# 更新商品
def update_product(product_id, title, description, price, category, condition, contact_info, image_path=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 准备更新语句，根据是否有新图片来决定是否更新image_path字段
        if image_path:
            c.execute(
                '''UPDATE products SET title = ?, description = ?, price = ?, category = ?, 
                   condition = ?, contact_info = ?, image_path = ? 
                   WHERE id = ?''',
                (title, description, price, category, condition, contact_info, image_path, product_id)
            )
        else:
            c.execute(
                '''UPDATE products SET title = ?, description = ?, price = ?, category = ?, 
                   condition = ?, contact_info = ? 
                   WHERE id = ?''',
                (title, description, price, category, condition, contact_info, product_id)
            )
        conn.commit()
        return True, t('product.updated_success')
    except Exception as e:
        return False, f"{t('product.publish_failed')}: {str(e)}"
    finally:
        conn.close()

# 删除商品
def delete_product(product_id):
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        c.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        return True, t('product.deleted_success')
    except Exception as e:
        return False, f"删除失败: {str(e)}"
    finally:
        conn.close()

# 商品发布页面
def product_publish_page():
    if not st.session_state.get('user'):
        st.warning(t('auth.login_required'))
        return
    
    st.title(t('page_titles.publish'))
    
    with st.form("product_form"):
        title = st.text_input(t('product.product_name'))
        category = st.selectbox(t('product.category'), 
                               [t('product.categories.electronics'), t('product.categories.household'), 
                                t('product.categories.clothing'), t('product.categories.books'), 
                                t('product.categories.sports'), t('product.categories.other')])
        condition = st.selectbox(t('product.condition'), 
                                [t('product.conditions.new'), t('product.conditions.like_new'), 
                                 t('product.conditions.minor_wear'), t('product.conditions.normal'), 
                                 t('product.conditions.heavy_wear')])
        price = st.number_input(t('product.price'), min_value=0.01, format="%.2f")
        description = st.text_area(t('product.description'))
        contact_info = st.text_input(t('product.contact_info'))
        
        # 图片上传功能
        image = st.file_uploader(t('product.upload_image'), type=["jpg", "jpeg", "png"])
        
        submit = st.form_submit_button(t('product.submit'))
        
        if submit:
            if not all([title, category, condition, price, description, contact_info]):
                st.error(t('product.fill_required'))
            else:
                # 这里简化处理，实际应用中可以保存图片
                image_path = None
                if image:
                    # 实际应用中可以保存图片到文件系统并记录路径
                    image_path = f"images/{datetime.now().timestamp()}_{image.name}"
                
                success, message = publish_product(
                    st.session_state.user['id'],
                    title, description, price, category, condition, contact_info, image_path
                )
                
                if success:
                    st.success(message)
                else:
                    st.error(message)

# 商品管理页面
def product_management_page():
    if not st.session_state.get('user'):
        st.warning(t('auth.login_required'))
        return
    
    st.title(t('page_titles.my_products'))
    products = get_user_products(st.session_state.user['id'])
    
    if not products:
        st.info(t('product.no_products'))
        return
    
    for product in products:
        with st.expander(f"{product['title']} - ¥{product['price']}"):
            col1, col2 = st.columns(2)
            with col1:
                # 将数据库中的中文类别转换为当前语言
                cat_key = get_category_key(product['category'])
                st.write(f"{t('product.category')}: {t(f'product.categories.{cat_key}')}")
                
                # 将数据库中的中文新旧程度转换为当前语言
                cond_key = get_condition_key(product['condition'])
                st.write(f"{t('product.condition')}: {t(f'product.conditions.{cond_key}')}")
                st.write(f"{t('product.created_at')}: {product['created_at']}")
                st.write(f"{t('product.contact_info')}: {product['contact_info']}")
            
            with col2:
                st.write(t('product.description') + ":")
                st.write(product['description'])
                
                # 编辑和删除功能
                if st.button(t('product.edit'), key=f"edit_{product['id']}"):
                    # 设置编辑状态，存储当前编辑的商品ID
                    st.session_state.editing_product = product['id']
                    
                if st.button(t('product.delete'), key=f"delete_{product['id']}", type="primary"):
                    # 显示确认对话框
                    if st.session_state.get('confirming_delete') == product['id']:
                        # 确认删除
                        success, message = delete_product(product['id'])
                        if success:
                            st.success(message)
                            # 重新加载页面以更新商品列表
                            st.rerun()
                        else:
                            st.error(message)
                        # 清除确认状态
                        st.session_state.confirming_delete = None
                    else:
                        # 第一次点击删除按钮，显示确认提示
                        st.warning(t('product.confirm_delete'))
                        st.session_state.confirming_delete = product['id']
                        # 刷新页面以显示确认状态
                        st.rerun()
        
        # 处理编辑功能
        if 'editing_product' in st.session_state and st.session_state.editing_product == product['id']:
            st.subheader(t('product.update_button'))
            with st.form(f"edit_form_{product['id']}"):
                # 预填充表单字段
                edit_title = st.text_input(t('product.product_name'), value=product['title'])
                # 获取当前商品类别的翻译键
                current_category_key = get_category_key(product['category'])
                current_category_text = t(f'product.categories.{current_category_key}')
                
                # 类别选项列表
                category_options = [
                    t('product.categories.electronics'),
                    t('product.categories.household'),
                    t('product.categories.clothing'),
                    t('product.categories.books'),
                    t('product.categories.sports'),
                    t('product.categories.other')
                ]
                
                # 找到当前类别的索引
                category_index = category_options.index(current_category_text)
                
                edit_category = st.selectbox(
                    t('product.category'),
                    category_options,
                    index=category_index
                )
                # 获取当前商品状态的翻译键
                current_condition_key = get_condition_key(product['condition'])
                current_condition_text = t(f'product.conditions.{current_condition_key}')
                
                # 状态选项列表
                condition_options = [
                    t('product.conditions.new'),
                    t('product.conditions.like_new'),
                    t('product.conditions.minor_wear'),
                    t('product.conditions.normal'),
                    t('product.conditions.heavy_wear')
                ]
                
                # 找到当前状态的索引
                condition_index = condition_options.index(current_condition_text)
                
                edit_condition = st.selectbox(
                    t('product.condition'),
                    condition_options,
                    index=condition_index
                )
                edit_price = st.number_input(t('product.price'), min_value=0.01, format="%.2f", value=product['price'])
                edit_description = st.text_area(t('product.description'), value=product['description'])
                edit_contact_info = st.text_input(t('product.contact_info'), value=product['contact_info'])
                
                # 图片上传功能（可选）
                edit_image = st.file_uploader(t('product.upload_image'), type=["jpg", "jpeg", "png"], accept_multiple_files=False)
                
                # 提交和取消按钮
                col_submit, col_cancel = st.columns(2)
                with col_submit:
                    submit_edit = st.form_submit_button(t('product.update_button'), type="primary")
                with col_cancel:
                    cancel_edit = st.form_submit_button(t('common.cancel'))
                
                if submit_edit:
                    if not all([edit_title, edit_category, edit_condition, edit_price, edit_description, edit_contact_info]):
                        st.error(t('product.fill_required'))
                    else:
                        # 处理图片（如果有新上传）
                        edit_image_path = product['image_path']  # 默认保留原图片
                        if edit_image:
                            # 实际应用中可以保存图片到文件系统并记录路径
                            edit_image_path = f"images/{datetime.now().timestamp()}_{edit_image.name}"
                        
                        success, message = update_product(
                            product['id'],
                            edit_title, edit_description, edit_price, edit_category, edit_condition, edit_contact_info, edit_image_path
                        )
                        
                        if success:
                            st.success(message)
                            # 清除编辑状态并重新加载页面
                            del st.session_state.editing_product
                            st.rerun()
                        else:
                            st.error(message)
                
                if cancel_edit:
                    # 清除编辑状态并刷新页面
                    del st.session_state.editing_product
                    st.rerun()
