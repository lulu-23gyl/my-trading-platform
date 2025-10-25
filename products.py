import streamlit as st
from database import get_db_connection
from datetime import datetime
from language import t
from search import get_category_key, get_condition_key

# 发布商品
def publish_product(user_id, title, descriptions, price, category, condition, contact_info, image_path=None):
    conn = get_db_connection()
    c = conn.cursor()
    
    try:
        # 获取各语言描述，如果没有提供则使用默认语言(中文)的描述
        description_zh = descriptions.get('zh', '')
        description_en = descriptions.get('en', description_zh)  # 如果没有英文，使用中文
        description_ja = descriptions.get('ja', description_zh)  # 如果没有日文，使用中文
        description_ko = descriptions.get('ko', description_zh)  # 如果没有韩文，使用中文
        
        c.execute(
            '''INSERT INTO products 
               (user_id, title, description_zh, description_en, description_ja, description_ko, 
                price, category, condition, contact_info, image_path, created_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, title, description_zh, description_en, description_ja, description_ko, 
             price, category, condition, contact_info, image_path, datetime.now())
        )
        conn.commit()
        return True, t('product.publish_success')
    except Exception as e:
        return False, f"{t('product.publish_failed')}: {str(e)}"
    finally:
        conn.close()

# 获取用户发布的所有商品
def get_user_products(user_id):
    conn = get_db_connection()
    # 只获取产品ID列表
    product_ids = [row['id'] for row in conn.execute(
        'SELECT * FROM products WHERE user_id = ? ORDER BY created_at DESC', 
        (user_id,)
    ).fetchall()]
    conn.close()
    
    # 使用get_product_details函数处理每个产品，以支持多语言描述
    products = []
    for product_id in product_ids:
        product = get_product_details(product_id)
        if product:
            products.append(product)
    
    return products

# 获取商品详情
def get_product_details(product_id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    conn.close()
    
    # 如果找不到产品，返回None
    if not product:
        return None
    
    # 获取当前语言的描述
    from language import get_current_language
    current_lang = get_current_language()
    
    # 为了保持向后兼容性，我们添加一个description属性，根据当前语言返回相应的描述
    class ProductWithLangDesc:
        def __init__(self, original_product):
            # 将SQLite Row对象转换为可修改的字典
            self.__dict__ = dict(original_product)
            
        def __getitem__(self, key):
            if key == 'description':
                # 根据当前语言返回相应的描述字段
                lang_desc_key = f'description_{get_current_language()}'
                # 如果特定语言的描述为空，则尝试回退到中文描述
                if lang_desc_key in self.__dict__ and self.__dict__[lang_desc_key]:
                    return self.__dict__[lang_desc_key]
                elif 'description_zh' in self.__dict__ and self.__dict__['description_zh']:
                    return self.__dict__['description_zh']
                else:
                    return ''
            return self.__dict__[key]
            
        def get(self, key, default=None):
            if key == 'description':
                try:
                    return self[key]
                except KeyError:
                    return default
            return self.__dict__.get(key, default)
    
    return ProductWithLangDesc(product)

# 根据当前语言获取商品描述
def get_product_description(product):
    from language import get_current_language
    current_lang = get_current_language()
    
    # 尝试获取当前语言的描述
    lang_desc_key = f'description_{current_lang}'
    
    # 同时支持对象和字典格式的产品数据
    if isinstance(product, dict):
        # 优先使用当前语言描述
        if product.get(lang_desc_key):
            return product[lang_desc_key]
        # 降级到中文描述
        elif product.get('description_zh'):
            return product['description_zh']
        # 最后使用原始description字段
        elif product.get('description'):
            return product['description']
    else:
        # 对象格式的处理
        if hasattr(product, lang_desc_key) and getattr(product, lang_desc_key):
            return getattr(product, lang_desc_key)
        # 降级到中文描述
        elif hasattr(product, 'description_zh') and getattr(product, 'description_zh'):
            return getattr(product, 'description_zh')
        # 最后使用原始description字段
        elif hasattr(product, 'description'):
            return getattr(product, 'description')
    
    return ''

# 更新商品
def update_product(product_id, title, descriptions, price, category, condition, contact_info, image_path=None):
    conn = get_db_connection()
    try:
        # 准备更新语句
        update_fields = ['title = ?', 'price = ?', 'category = ?', 'condition = ?', 'contact_info = ?']
        update_values = [title, price, category, condition, contact_info]
        
        # 处理多语言描述字段
        if isinstance(descriptions, dict):
            # 为每种支持的语言设置描述
            for lang in ['zh', 'en', 'ja', 'ko']:
                update_fields.append(f'description_{lang} = ?')
                update_values.append(descriptions.get(lang, ''))
            # 设置默认description字段为中文描述（向后兼容）
            update_fields.append('description = ?')
            update_values.append(descriptions.get('zh', ''))
        else:
            # 向后兼容，单字符串描述
            update_fields.append('description_zh = ?')
            update_fields.append('description = ?')
            update_values.append(descriptions)  # 同时更新zh版本和默认版本
            # 其他语言保持为空
            for lang in ['en', 'ja', 'ko']:
                update_fields.append(f'description_{lang} = ?')
                update_values.append('')
        
        # 如果提供了图片路径，则更新
        if image_path:
            update_fields.append('image_path = ?')
            update_values.append(image_path)
        
        # 添加WHERE子句和product_id
        update_values.append(product_id)
        
        # 构建SQL语句
        sql = f"UPDATE products SET {', '.join(update_fields)} WHERE id = ?"
        
        # 执行更新
        conn.execute(sql, update_values)
        conn.commit()
        
        return True, "商品更新成功！"
    except Exception as e:
        conn.rollback()
        return False, f"更新失败: {str(e)}"
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
        
        # 多语言描述输入
        st.subheader(t('product.multilingual_description'))
        descriptions = {}
        
        # 获取当前语言
        from language import get_current_language, LANGUAGES
        current_lang = get_current_language()
        
        # 首先显示当前语言的描述输入框
        descriptions[current_lang] = st.text_area(
            f"{t('product.product_description')} ({LANGUAGES[current_lang]})")
        
        # 然后显示其他语言的描述输入框（可选）
        for lang in LANGUAGES.keys():
            if lang != current_lang:
                descriptions[lang] = st.text_area(
                    f"{t('product.product_description')} ({LANGUAGES[lang]})", 
                    placeholder=t('product.optional_description'),
                    key=f"desc_{lang}")
        # 保留原始description变量以保持向后兼容，但实际使用多语言描述
        description = descriptions.get(get_current_language(), '')
        contact_info = st.text_input(t('product.contact_info'))
        
        # 图片上传功能
        image = st.file_uploader(t('product.upload_image'), type=["jpg", "jpeg", "png"])
        
        submit = st.form_submit_button(t('product.submit'))
        
        if submit:
            # 检查必填字段
            if not all([title, category, condition, price, contact_info]):
                st.error(t('product.fill_required'))
            elif not any(descriptions.values()):  # 至少要有一个语言的描述
                st.error(t('product.at_least_one_description_required'))
            else:
                # 处理图片上传，实际保存到文件系统
                image_path = None
                if image:
                    # 确保images目录存在
                    import os
                    if not os.path.exists('images'):
                        os.makedirs('images')
                    
                    # 生成唯一的文件名并保存图片
                    image_path = f"images/{datetime.now().timestamp()}_{image.name}"
                    with open(image_path, "wb") as f:
                        f.write(image.getbuffer())
                    st.success(f"图片已成功上传: {image.name}")
                
                success, message = publish_product(
                    st.session_state.user['id'],
                    title, descriptions, price, category, condition, contact_info, image_path
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
                
                # 如果有图片路径，先检查文件是否存在再显示
                if product['image_path']:
                    import os
                    if os.path.exists(product['image_path']):
                        st.subheader(t("product.product_image"))
                        st.image(product['image_path'], width=200)
                    else:
                        st.warning(t("product.image_not_found"))
            
            with col2:
                # 使用当前语言显示商品描述
                st.write(f"**{t('product.description')}:** {product['description']}")
                
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
                
                # 多语言描述编辑
                st.subheader(t('product.multilingual_description'))
                edit_descriptions = {}
                
                # 获取当前语言
                from language import get_current_language, LANGUAGES
                current_lang = get_current_language()
                
                # 尝试从产品对象获取各语言描述
                for lang in LANGUAGES.keys():
                    desc_key = f'description_{lang}'
                    # 如果有该语言的描述字段且存在值，则使用该值，否则使用当前语言的description
                    if hasattr(product, desc_key) and getattr(product, desc_key):
                        default_desc = getattr(product, desc_key)
                    elif product.get(desc_key):
                        default_desc = product[desc_key]
                    else:
                        default_desc = product['description']
                    
                    # 为每种语言创建文本区域
                    edit_descriptions[lang] = st.text_area(
                        f"{t('product.product_description')} ({LANGUAGES[lang]})",
                        value=default_desc,
                        key=f"edit_desc_{lang}_{product['id']}")
                
                # 保留原始edit_description变量以保持向后兼容
                edit_description = edit_descriptions.get(current_lang, '')
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
                            # 确保images目录存在
                            import os
                            if not os.path.exists('images'):
                                os.makedirs('images')
                            
                            # 生成唯一的文件名并保存图片
                            edit_image_path = f"images/{datetime.now().timestamp()}_{edit_image.name}"
                            with open(edit_image_path, "wb") as f:
                                f.write(edit_image.getbuffer())
                            st.success(f"图片已成功更新: {edit_image.name}")
                        
                        # 检查必填字段
                        if not any(edit_descriptions.values()):  # 至少要有一个语言的描述
                            st.error(t('product.at_least_one_description_required'))
                        else:
                            success, message = update_product(
                                product['id'],
                                edit_title, edit_descriptions, edit_price, edit_category, edit_condition, edit_contact_info, edit_image_path
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
