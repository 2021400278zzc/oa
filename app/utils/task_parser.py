import re

def parse_task_requirements(detail_task: str) -> list:
    """
    解析任务需求文本，提取小任务列表
    
    Args:
        detail_task (str): 详细任务需求文本
        
    Returns:
        list: 小任务列表，每个任务包含id和子任务内容
    """
    tasks = []
    current_task = None
    current_sub_tasks = []
    
    # 忽略的标题列表
    ignored_sections = [
        r'#+\s*注意事项',
        r'#+\s*连贯性说明',
        r'#+\s*说明',
        r'#+\s*补充说明',
        r'遇到问题优先查阅',
        r'所有代码需保存为'
    ]
    
    # 优先使用markdown标题分割任务
    markdown_sections = re.split(r'(#{1,4}\s+\*\*\d+\.\s+.+?\*\*)', detail_task)
    
    # 如果成功分割了文本（至少包含一个标题）
    if len(markdown_sections) > 1:
        # 第一个元素可能是前言部分，跳过
        for i in range(1, len(markdown_sections), 2):
            if i + 1 < len(markdown_sections):
                header = markdown_sections[i]
                content = markdown_sections[i + 1]
                
                # 提取标题中的编号
                header_match = re.match(r'#{1,4}\s+\*\*(\d+)\.\s+(.+?)\*\*', header)
                if header_match:
                    task_id = header_match.group(1)
                    
                    # 清理内容中的注意事项、连贯性说明等
                    lines = content.split('\n')
                    filtered_lines = []
                    
                    ignore_mode = False
                    for line in lines:
                        line_text = line.strip()
                        if not line_text:
                            continue
                            
                        # 检查是否应该忽略此行
                        for pattern in ignored_sections:
                            if re.search(pattern, line_text) or "遇到问题优先查阅" in line_text or "连贯性说明" in line_text or "所有代码需保存为" in line_text:
                                ignore_mode = True
                                break
                                
                        if ignore_mode:
                            # 如果遇到新的子标题或列表项，退出忽略模式
                            if line_text.startswith('-') or re.match(r'^\*\*.*\*\*', line_text):
                                ignore_mode = False
                            else:
                                continue
                        
                        # 处理子任务
                        if line_text.startswith('-'):
                            # 处理列表项
                            sub_task_text = line_text[1:].strip()
                            
                            # 保存代码块中的内容
                            code_blocks = {}
                            code_count = 0
                            
                            # 先保存内联代码块
                            def save_code(match):
                                nonlocal code_count
                                placeholder = f"__CODE_{code_count}__"
                                code_blocks[placeholder] = match.group(1)
                                code_count += 1
                                return placeholder
                            
                            # 先替换内联代码块为占位符
                            processed_text = re.sub(r'`([^`]+)`', save_code, sub_task_text)
                            
                            # 移除Markdown链接语法，保留文本
                            processed_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', processed_text)
                            
                            # 移除Markdown强调语法，但保留内容
                            processed_text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', processed_text)
                            processed_text = re.sub(r'\*([^\*]+)\*', r'\1', processed_text)
                            
                            # 还原代码块内容
                            for placeholder, code in code_blocks.items():
                                processed_text = processed_text.replace(placeholder, code)
                            
                            filtered_lines.append(processed_text)
                        else:
                            # 保存代码块中的内容
                            code_blocks = {}
                            code_count = 0
                            
                            # 先保存内联代码块
                            def save_code(match):
                                nonlocal code_count
                                placeholder = f"__CODE_{code_count}__"
                                code_blocks[placeholder] = match.group(1)
                                code_count += 1
                                return placeholder
                            
                            # 先替换内联代码块为占位符
                            processed_text = re.sub(r'`([^`]+)`', save_code, line_text)
                            
                            # 移除Markdown强调语法，但保留内容
                            processed_text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', processed_text)
                            processed_text = re.sub(r'\*([^\*]+)\*', r'\1', processed_text)
                            
                            # 还原代码块内容
                            for placeholder, code in code_blocks.items():
                                processed_text = processed_text.replace(placeholder, code)
                            
                            filtered_lines.append(processed_text)
                    
                    # 合并行，保留换行结构
                    task_content = '\n'.join(filtered_lines)
                    
                    tasks.append({
                        'id': task_id,
                        'sub_tasks': task_content
                    })
        
        return tasks
    
    # 如果按标题分割失败，则使用原来的逐行解析方法
    lines = detail_task.split('\n')
    
    ignore_mode = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 检查是否进入忽略模式
        for pattern in ignored_sections:
            if re.match(pattern, line) or "遇到问题优先查阅" in line or "连贯性说明" in line:
                ignore_mode = True
                break
        
        if ignore_mode:
            # 如果遇到新的任务标题，则退出忽略模式
            if re.match(r'#{1,4}\s+\*\*\d+\.\s+.+?\*\*', line) or re.match(r'^(\d+)\.\s+\*\*(.+?)\*\*', line):
                ignore_mode = False
            else:
                continue
            
        # 匹配Markdown格式的标题任务（#### **1. 标题**）
        markdown_header_match = re.match(r'#{1,4}\s+\*\*(\d+)\.\s+(.+?)\*\*', line)
        if markdown_header_match:
            if current_task and current_sub_tasks:
                # 将子任务列表合并，保留换行
                current_task['sub_tasks'] = '\n'.join(current_sub_tasks)
                tasks.append(current_task)
            
            current_task = {
                'id': markdown_header_match.group(1),
                'sub_tasks': ''
            }
            current_sub_tasks = []
            continue
            
        # 匹配主要任务标题（数字编号）
        main_task_match = re.match(r'^(\d+)\.\s+\*\*(.+?)\*\*', line)
        if main_task_match:
            if current_task and current_sub_tasks:
                # 将子任务列表合并，保留换行
                current_task['sub_tasks'] = '\n'.join(current_sub_tasks)
                tasks.append(current_task)
            
            current_task = {
                'id': main_task_match.group(1),
                'sub_tasks': ''
            }
            current_sub_tasks = []
            continue
        
        # 匹配内容标题（**内容**：）
        content_title_match = re.match(r'^\s*\*\*(.+?)\*\*\s*：', line)
        if content_title_match and current_task:
            content_title = content_title_match.group(1)
            current_sub_tasks.append(f"{content_title}：")
            continue
            
        # 匹配子任务（减号列表）
        sub_task_match = re.match(r'^\s*-\s+(.+)', line)
        if sub_task_match and current_task:
            # 跳过包含忽略关键词的子任务
            sub_task_text = sub_task_match.group(1)
            if any(ignore_keyword in sub_task_text for ignore_keyword in ["遇到问题优先查阅", "连贯性说明", "所有代码需保存为"]):
                continue
            
            # 保存代码块中的内容
            code_blocks = {}
            code_count = 0
            
            # 先保存内联代码块
            def save_code(match):
                nonlocal code_count
                placeholder = f"__CODE_{code_count}__"
                code_blocks[placeholder] = match.group(1)
                code_count += 1
                return placeholder
            
            # 先替换内联代码块为占位符
            processed_text = re.sub(r'`([^`]+)`', save_code, sub_task_text)
            
            # 移除Markdown链接语法，保留文本
            processed_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', processed_text)
            
            # 移除Markdown强调语法，但保留内容
            processed_text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', processed_text)
            processed_text = re.sub(r'\*([^\*]+)\*', r'\1', processed_text)
            
            # 还原代码块内容
            for placeholder, code in code_blocks.items():
                processed_text = processed_text.replace(placeholder, code)
            
            current_sub_tasks.append(processed_text.strip())
            continue
            
        # 匹配任务验收标准中的待办项
        checklist_match = re.match(r'^\s*\[([ x])\]\s+(.+)', line)
        if checklist_match and current_task:
            checklist_text = checklist_match.group(2)
            # 跳过包含忽略关键词的待办项
            if any(ignore_keyword in checklist_text for ignore_keyword in ["遇到问题优先查阅", "连贯性说明", "所有代码需保存为"]):
                continue
                
            # 保存代码块中的内容
            code_blocks = {}
            code_count = 0
            
            # 先保存内联代码块
            def save_code(match):
                nonlocal code_count
                placeholder = f"__CODE_{code_count}__"
                code_blocks[placeholder] = match.group(1)
                code_count += 1
                return placeholder
            
            # 先替换内联代码块为占位符
            processed_text = re.sub(r'`([^`]+)`', save_code, checklist_text)
            
            # 移除Markdown强调语法，但保留内容
            processed_text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', processed_text)
            processed_text = re.sub(r'\*([^\*]+)\*', r'\1', processed_text)
            
            # 还原代码块内容
            for placeholder, code in code_blocks.items():
                processed_text = processed_text.replace(placeholder, code)
                
            current_sub_tasks.append(processed_text.strip())
            continue
            
        # 其他内容行
        if current_task:
            # 跳过包含忽略关键词的行
            if any(ignore_keyword in line for ignore_keyword in ["遇到问题优先查阅", "连贯性说明", "所有代码需保存为"]):
                continue
            
            # 保存代码块中的内容
            code_blocks = {}
            code_count = 0
            
            # 先保存内联代码块
            def save_code(match):
                nonlocal code_count
                placeholder = f"__CODE_{code_count}__"
                code_blocks[placeholder] = match.group(1)
                code_count += 1
                return placeholder
            
            # 先替换内联代码块为占位符
            processed_text = re.sub(r'`([^`]+)`', save_code, line)
            
            # 移除Markdown强调语法，但保留内容
            processed_text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', processed_text)
            processed_text = re.sub(r'\*([^\*]+)\*', r'\1', processed_text)
            
            # 还原代码块内容
            for placeholder, code in code_blocks.items():
                processed_text = processed_text.replace(placeholder, code)
            
            current_sub_tasks.append(processed_text)
    
    # 添加最后一个任务
    if current_task and current_sub_tasks:
        current_task['sub_tasks'] = '\n'.join(current_sub_tasks)
        tasks.append(current_task)
    
    # 如果仍然没有任务，将整个文本作为一个任务，排除注意事项等
    if not tasks and detail_task.strip():
        lines = detail_task.split('\n')
        filtered_lines = []
        for line in lines:
            skip_line = False
            for pattern in ignored_sections:
                if re.search(pattern, line) or "遇到问题优先查阅" in line or "连贯性说明" in line or "所有代码需保存为" in line:
                    skip_line = True
                    break
            if not skip_line:
                # 保存代码块中的内容
                code_blocks = {}
                code_count = 0
                
                # 先保存内联代码块
                def save_code(match):
                    nonlocal code_count
                    placeholder = f"__CODE_{code_count}__"
                    code_blocks[placeholder] = match.group(1)
                    code_count += 1
                    return placeholder
                
                # 先替换内联代码块为占位符
                processed_text = re.sub(r'`([^`]+)`', save_code, line)
                
                # 移除Markdown强调语法，但保留内容
                processed_text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', processed_text)
                processed_text = re.sub(r'\*([^\*]+)\*', r'\1', processed_text)
                
                # 还原代码块内容
                for placeholder, code in code_blocks.items():
                    processed_text = processed_text.replace(placeholder, code)
                
                filtered_lines.append(processed_text)
        
        tasks.append({
            'id': '1',
            'sub_tasks': '\n'.join(filtered_lines).strip()
        })
    
    # 清理每个任务的sub_tasks内容，去掉额外文本
    for task in tasks:
        sub_tasks = task['sub_tasks']
        # 如果包含"注意事项"或"连贯性说明"，只保留前面的部分
        for pattern in ["注意事项", "连贯性说明", "遇到问题优先查阅", "所有代码需保存为"]:
            if pattern in sub_tasks:
                parts = sub_tasks.split(pattern, 1)
                sub_tasks = parts[0].strip()
        task['sub_tasks'] = sub_tasks
    
    return tasks 