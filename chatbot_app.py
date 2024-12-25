import streamlit as st
from datetime import datetime
import base64
import os
from dotenv import load_dotenv
import requests
import json
import uuid
import threading
import time

st.set_page_config(page_title="Claude Chat", layout="wide")

# .env文件
load_dotenv()
api_key=os.getenv('CLAUDE_API_KEY', '')
url=os.getenv('CLAUDE_BASE_URL', '')

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}',
    "anthropic-version": "2023-06-01",
}

# 初始化session state
if 'conversation_groups' not in st.session_state:
    st.session_state['conversation_groups'] = [
        {
            'id': str(uuid.uuid4()),
            'name': '对话 1',
            'messages': [],
            'system_prompt': '',
            'document': '',
            'user_prompt':'',
            # 新增模型参数
            'model': 'claude-3-5-haiku-20241022',
            'temperature': 1.0,
            'max_tokens': 2000
        }
    ]

if 'current_page' not in st.session_state:
    st.session_state['current_page'] = st.session_state['conversation_groups'][0]['id']

# 添加新的对话组的函数
def add_conversation_group(name=None):
    if name is None:
        name = f'对话 {len(st.session_state["conversation_groups"]) + 1}'

    new_group = {
        'id': str(uuid.uuid4()),
        'name': name,
        'messages': [],
        'system_prompt': '',
        'document': '',
        'user_prompt':'',
        # 新增模型参数
        'model': 'claude-3-5-haiku-20241022',
        'temperature': 1.0,
        'max_tokens': 2000
    }

    st.session_state['conversation_groups'].insert(0, new_group)
    st.session_state['current_page'] = new_group['id']
    return new_group['id']

# 创建侧边栏
def create_sidebar():
    st.sidebar.subheader("会话管理")

    # 显示所有对话组作为导航
    for index, group in enumerate(st.session_state['conversation_groups']):
        col1, col2, col3 = st.sidebar.columns([1.0, 1.0,1.0])
        with col1:
            if col1.button(f"{group['name']}", key=f"nav_{group['id']}"):
                st.session_state['current_page'] = group['id']
                st.rerun()

        with col2:
            if st.button("传递", key=f"transmit_{group['id']}"):
                # 查找当前对话组
                current_group = next(
                    (g for g in st.session_state['conversation_groups'] 
                    if g['id'] == group['id']), 
                    None
                )

                if current_group:
                    # 找到当前对话组的最后一个助手消息
                    last_assistant_msg = [msg['content'] for msg in current_group['messages'] if msg['role'] == 'assistant']

                    # 创建新的对话组
                    new_group_id = add_conversation_group()
                    new_group = next(group for group in st.session_state['conversation_groups'] if group['id'] == new_group_id)

                    # 如果有助手消息，将最后一个消息作为文档传递
                    if last_assistant_msg:
                        new_group['document'] = last_assistant_msg[-1]

                    # 复制其他可能有用的属性
                    new_group['system_prompt'] = current_group.get('system_prompt', '')
                    new_group['user_prompt'] = current_group.get('user_prompt', '')

                    # 复制模型参数
                    new_group['model'] = current_group.get('model', 'claude-3-5-haiku-20241022')
                    new_group['temperature'] = current_group.get('temperature', 1.0)
                    new_group['max_tokens'] = current_group.get('max_tokens', 2000)

                    st.rerun()

        with col3:
            if st.button("继承", key=f"inherit_{group['id']}"):
                # 找到当前选中的对话组
                current_group = next(
                    (g for g in st.session_state['conversation_groups'] 
                    if g['id'] == st.session_state['current_page']), 
                    None
                )

                if current_group:
                    new_group_id = add_conversation_group()
                    new_group = next(group for group in st.session_state['conversation_groups'] if group['id'] == new_group_id)

                    # 复制当前对话组的所有属性
                    new_group['system_prompt'] = current_group.get('system_prompt', '')
                    new_group['document'] = current_group.get('document', '')
                    new_group['user_prompt'] = current_group.get('user_prompt', '')
                    new_group['messages'] = current_group.get('messages', [])

                    # 复制模型参数
                    new_group['model'] = current_group.get('model', 'claude-3-5-haiku-20241022')
                    new_group['temperature'] = current_group.get('temperature', 1.0)
                    new_group['max_tokens'] = current_group.get('max_tokens', 2000)

                    st.rerun()

    # 添加新对话
    if st.sidebar.button("➕ 新对话"):
        add_conversation_group()
        st.rerun()

    # 加载对话
    log_files = [f for f in os.listdir("chat_logs") if f.endswith(".json")]
    selected_file = st.sidebar.selectbox("选择对话记录", log_files)

    if st.sidebar.button("➕加载对话"):
        if selected_file:
            try:
                with open(os.path.join("chat_logs", selected_file), 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)

                # 创建新的对话组
                new_group_id = add_conversation_group(chat_data.get('name', '重加载'))
                new_group = next(group for group in st.session_state['conversation_groups'] if group['id'] == new_group_id)

                # 恢复对话内容
                new_group['messages'] = chat_data.get('messages', [])
                new_group['system_prompt'] = chat_data.get('system_prompt', '')
                new_group['document'] = chat_data.get('document', '')
                new_group['user_prompt'] = chat_data.get('user_prompt', '')
                # 恢复模型参数
                new_group['model'] = chat_data.get('model', 'claude-3-5-haiku-20241022')
                new_group['temperature'] = chat_data.get('temperature', 1.0)
                new_group['max_tokens'] = chat_data.get('max_tokens', 2000)

                st.sidebar.success(f"成功加载对话：{selected_file}")
                st.rerun()

            except Exception as e:
                st.sidebar.error(f"加载对话时出错：{str(e)}")

def get_current_group():
    return next((group for group in st.session_state['conversation_groups'] 
                if group['id'] == st.session_state['current_page']), None)

def handle_chat_command(user_input, current_group):
    # 处理命令
    # /N 名称 - 创建新对话
    # /RN 新名称 - 重命名当前对话
    # /DEL - 删除当前对话
    if user_input.startswith("/N"):
        # 提取新对话名称
        parts = user_input.split(" ", 1)
        name = parts[1] if len(parts) > 1 else None

        # 创建新对话
        new_id = add_conversation_group(name)
        return True, f"已创建新对话: {name if name else '对话 ' + str(len(st.session_state['conversation_groups']))}"

    elif user_input.startswith("/RN"):
        # 重命名当前对话
        parts = user_input.split(" ", 1)
        if len(parts) > 1:
            current_group['name'] = parts[1]
            return True, f"已将当前对话重命名为: {parts[1]}"
        return True, "请提供新名称"

    elif user_input == "/DEL":
        # 删除当前对话
        if len(st.session_state['conversation_groups']) > 1:
            st.session_state['conversation_groups'] = [
                g for g in st.session_state['conversation_groups'] 
                if g['id'] != current_group['id']
            ]
            st.session_state['current_page'] = st.session_state['conversation_groups'][0]['id']
            return True, "已删除当前对话"
        return True, "无法删除最后一个对话"

    return False, None

def render_chat_interface(group):
    # 显示当前对话历史
    container = st.container()
    with container:
        # 系统提示词展示
        with st.chat_message(name="user", avatar="pathway/to/static/role.png"):
            system_placeholder = st.empty()
            if group['system_prompt']:
                system_placeholder.markdown(f"```\n{group['system_prompt']}\n```")

        # 文档展示
        with st.chat_message(name="user", avatar="pathway/to/document.png"):
            document_placeholder = st.empty()
            if group['document']:
                document_placeholder.markdown(f"```\n{group['document']}\n```")    

        # 显示已有消息
        for message in group['messages']:
            if message["role"] == "user":
                with st.chat_message(message["role"], avatar="pathway/to/user.png"):
                    st.markdown(f"```\n{message['content']}\n```")
            elif message["role"] == "assistant":
                with st.chat_message(message["role"], avatar="pathway/to/assistant.png"):
                    st.markdown(message['content'])

        # 输入框
        with st.chat_message(name="user", avatar="pathway/to/user.png"):
            input_placeholder = st.empty()
        with st.chat_message(name="assistant", avatar="pathway/to/assistant.png"):
            message_placeholder = st.empty()

    return container, system_placeholder, document_placeholder, input_placeholder, message_placeholder

def main():
    # 创建侧边栏导航
    create_sidebar()

    # 获取当前对话组
    current_group = get_current_group()
    if not current_group:
        st.error("对话组不存在")
        return

    st.header(f"{current_group['name']}")

    # 渲染聊天界面
    container, system_placeholder, document_placeholder, input_placeholder, message_placeholder = render_chat_interface(current_group)

    # 对话表单
    with st.form(key=f"chat_form_{current_group['id']}"):
        # 模型和参数选择
        col1, col2, col3 = st.columns(3)
        with col1:
            model = st.selectbox("模型", 
                ["claude-3-5-haiku-20241022","claude-3-5-sonnet-20241022","claude-3-5-sonnet-20240620"],
                index=["claude-3-5-haiku-20241022","claude-3-5-sonnet-20241022","claude-3-5-sonnet-20240620"].index(current_group['model']))
        with col2:
            temperature = st.slider("Temperature", 0.0, 2.0, current_group['temperature'])
        with col3:
            max_tokens = st.slider("Max Tokens", 1, 8000, current_group['max_tokens'])

        # 系统提示词输入
        system_prompt = st.text_area("系统提示词", current_group['system_prompt'])

        # 文档输入
        document = st.text_area("文件", current_group['document'])

        # 用户提示词输入
        user_prompt = st.text_area("用户提示词", current_group['user_prompt'])

        # 操作按钮
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            send_btn = st.form_submit_button("发送")
        with col2:
            save_btn = st.form_submit_button("保存")
        with col3:
            clear_btn = st.form_submit_button("清除")
        with col4:
            balance_btn = st.form_submit_button("余额")

        # 发送消息逻辑
        if send_btn and user_prompt:
            # 更新对话组的模型参数
            current_group['model'] = model
            current_group['temperature'] = temperature
            current_group['max_tokens'] = max_tokens
            # 检查是否是命令
            is_command, response = handle_chat_command(user_prompt, current_group)

            if is_command:
                st.rerun()
            else:
                system = []
                current_group['user_prompt'] = user_prompt
                if system_prompt:
                    current_group['system_prompt'] = system_prompt
                    system_placeholder.markdown(f"```\n{system_prompt}\n```")
                    system.append({"type": "text", "text": system_prompt})
                if document:
                    current_group['document'] = document
                    document_placeholder.markdown(f"```\n{document}\n```")
                    system.append({"type": "text", "text": document})

                current_group['messages'].append({"role": "user", "content": user_prompt})
                input_placeholder.markdown(f"```\n{user_prompt}\n```")

                data = {
                    "model": model,
                    "system": system,
                    "messages": current_group['messages'],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": True
                }

                response = requests.post(url, headers=headers, json=data, stream=True)

                final_content = ""
                for chunk in response.iter_lines():
                    if chunk:
                        decoded_chunk = chunk.decode('utf-8')
                        if decoded_chunk.startswith('data:'):
                            json_chunk = json.loads(decoded_chunk[6:])
                            if json_chunk['type'] == 'content_block_delta':
                                content = json_chunk['delta']['text']
                                final_content += content
                                message_placeholder.markdown(final_content + "🖌️")

                current_group['messages'].append({"role": "assistant", "content": final_content})
                message_placeholder.markdown(final_content)

                st.rerun()

        # 清除对话逻辑
        if clear_btn:
            current_group['messages'] = []
            current_group['system_prompt'] = ''
            current_group['document'] = ''
            current_group['user_prompt'] = ''
            st.rerun()

        # 保存聊天记录逻辑
        if save_btn:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            chat_data = {
                "name": current_group['name'],
                "system_prompt": current_group['system_prompt'],
                "document": current_group['document'],
                "messages": current_group['messages'],
                # 添加模型参数
                "model": current_group['model'],
                "temperature": current_group['temperature'],
                "max_tokens": current_group['max_tokens']
            }

            # 创建保存目录（如果不存在）
            os.makedirs("chat_logs", exist_ok=True)

            # 保存为JSON文件
            with open(f"chat_logs/chat_{timestamp}.json", 'w', encoding="utf-8") as f:
                json.dump(chat_data, f, ensure_ascii=False, indent=4)

            st.success("聊天记录已保存为JSON文件")


        # 余额查询逻辑
        if balance_btn:
            try:
                billing_url = os.getenv('BILLING_URL','')
                headers_billing = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {api_key}'
                }
                response_billing = requests.post(billing_url, headers=headers_billing)
                balance = response_billing.json().get('total_available', 'N/A')
                st.success(f'余额: {balance}')
            except Exception as e:
                st.error(f"查询余额时出错: {str(e)}")

if __name__ == "__main__":
    main()
