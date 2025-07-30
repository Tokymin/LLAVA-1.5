import json
import os
import re


def fix_and_parse_cholec80(file_path):
    """修复并解析非标准的cholec80_qa_dataset.jsonl文件"""
    data = []
    current_object = {}
    current_key = None
    current_value = []
    in_array = False  # 标记是否在数组中

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # 处理对象开始和结束
            if line == '{':
                current_object = {}
                current_key = None
                current_value = []
                in_array = False
                continue
            elif line == '}':
                if current_key is not None and current_value:
                    # 处理最后一个键值对
                    value_str = ''.join(current_value).strip()
                    current_object[current_key] = parse_value(value_str)
                data.append(current_object)
                continue

            # 处理数组开始和结束
            if line.startswith('['):
                in_array = True
                current_value.append(line)
                continue
            if line.endswith(']'):
                in_array = False
                current_value.append(line)
                continue

            # 如果在数组中，直接累加内容
            if in_array:
                current_value.append(line)
                continue

            # 处理键值对（分割键和值）
            if ':' in line:
                # 如果之前有未处理的键值对，先处理
                if current_key is not None and current_value:
                    value_str = ''.join(current_value).strip()
                    current_object[current_key] = parse_value(value_str)

                # 解析新的键
                key_part, value_part = line.split(':', 1)
                current_key = key_part.strip().strip('"')
                current_value = [value_part.strip()]
            else:
                # 键值对的值跨多行，继续累加
                current_value.append(line)

    return data


def parse_value(value_str):
    """解析值并正确处理数组和字符串"""
    try:
        # 尝试直接JSON解析
        return json.loads(value_str)
    except:
        pass

    try:
        # 处理数组 - 提取引号中的内容
        if value_str.startswith('[') and value_str.endswith(']'):
            # 使用正则表达式提取引号中的内容
            items = re.findall(r'"([^"]+)"', value_str)
            if items:
                return items
    except:
        pass

    try:
        # 处理布尔值和null
        if value_str.lower() == 'true':
            return True
        elif value_str.lower() == 'false':
            return False
        elif value_str.lower() == 'null':
            return None
    except:
        pass

    try:
        # 处理数字
        if value_str.isdigit():
            return int(value_str)
        elif '.' in value_str and value_str.replace('.', '').isdigit():
            return float(value_str)
    except:
        pass

    # 处理字符串（去除引号）
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str[1:-1].replace('\\"', '"')

    # 作为原始字符串返回
    return value_str


def extract_id_from_path(frame_path, video_id):
    """
    从frame_path和video_id中提取ID，格式为25_00162_162
    适配目录格式为video25的情况
    """
    try:
        # 清理输入中的引号和逗号
        cleaned_frame_path = frame_path.strip().strip('",')
        cleaned_video_id = video_id.strip().strip('",')

        # 从video_id提取数字部分 (video25 -> 25)
        video_match = re.search(r'\d+', cleaned_video_id)
        if not video_match:
            raise ValueError(f"无法从video_id提取数字: {cleaned_video_id}")
        video_num = video_match.group()

        # 从frame_path提取中间编号
        # 处理两种目录格式: video25_00162 或 video25
        path_parts = cleaned_frame_path.split(os.sep)

        # 查找包含video和数字的目录部分
        dir_part = next((part for part in path_parts if cleaned_video_id in part), None)
        if not dir_part:
            raise ValueError(f"找不到包含video_id的目录: {cleaned_video_id}")

        # 提取中间编号 - 适配两种格式
        dir_parts = dir_part.split('_')
        if len(dir_parts) >= 2 and dir_parts[1].isdigit():
            # 格式1: video25_00162 -> 提取00162
            middle_num = dir_parts[1]
        else:
            # 格式2: video25 -> 从上级路径或文件名提取
            # 尝试从frame_path中提取类似00162的编号
            middle_match = re.search(r'video\d+_(\d+)', cleaned_frame_path)
            if middle_match:
                middle_num = middle_match.group(1)
            else:
                # 尝试从frame_id提取(备选方案)
                frame_id_match = re.search(r'frame_(\d+)_', os.path.basename(cleaned_frame_path))
                if frame_id_match:
                    middle_num = frame_id_match.group(1)
                else:
                    # 最终备选: 使用00000
                    middle_num = "00000"

        # 从frame_path提取帧编号 (frame_162_endo.png -> 162)
        frame_filename = os.path.basename(cleaned_frame_path)
        frame_match = re.search(r'frame_(\d+)_', frame_filename)
        if not frame_match:
            # 备选方案: 从文件名提取数字
            frame_match = re.search(r'(\d+)', frame_filename)

        if not frame_match:
            raise ValueError(f"无法从文件名提取帧编号: {frame_filename}")

        frame_num = frame_match.group(1)

        # 组合成目标ID格式
        return f"{video_num}_{middle_num}_{frame_num}"
    except Exception as e:
        # 打印错误信息以便调试
        print(f"提取ID时出错: {str(e)}")
        # 使用更可靠的备选方案
        fallback_video = re.search(r'\d+', cleaned_video_id).group() if re.search(r'\d+', cleaned_video_id) else "00"
        fallback_frame = re.search(r'\d+', cleaned_frame_path).group() if re.search(r'\d+',
                                                                                    cleaned_frame_path) else "000"
        return f"fallback_{fallback_video}_{fallback_frame}"

def convert_to_llava_format(cholec80_file, output_file):
    """将修复后的cholec80数据转换为llava格式"""
    # 修复并读取数据
    cholec80_data = fix_and_parse_cholec80(cholec80_file)
    print(f"成功解析 {len(cholec80_data)} 条数据")

    # 转换为llava格式
    llava_format_data = []

    for idx, item in enumerate(cholec80_data):
        # 提取关键信息
        video_id = item.get('video_id', f"video_{idx}")
        frame_id = item.get('frame_id', idx)
        phase = item.get('phase', "Unknown")
        frame_path = item.get('frame_path', "")

        # 确保tools是列表
        tools = item.get('tools', [])
        if not isinstance(tools, list):
            tools = [tools] if tools else []

        # 确保present_classes是列表
        present_classes = item.get('present_classes', [])
        if not isinstance(present_classes, list):
            present_classes = [present_classes] if present_classes else []

        risk_level = item.get('risk_level', 0)
        response = item.get('response', "")

        # 生成ID（格式：25_00162_162）
        unique_id = extract_id_from_path(frame_path, video_id)

        # 使用完整frame_path作为image值
        image_value = frame_path

        # 创建多轮对话
        conversations = []

        # 第一轮：询问手术阶段和工具
        conversations.append({
            "from": "human",
            "value": f"What is the current surgical phase and which tools are being used?\n<image>"
        })

        # AI回答
        tools_str = ", ".join(tools) if tools else "No tools"
        conversations.append({
            "from": "gpt",
            "value": f"The current surgical phase is {phase} and the tools being used are {tools_str}."
        })

        # 第二轮：询问解剖结构
        conversations.append({
            "from": "human",
            "value": "What anatomical structures are present in the image?"
        })

        # AI回答 - 修复解剖结构列表显示
        classes_str = ", ".join(present_classes) if present_classes else "No specific structures identified"
        conversations.append({
            "from": "gpt",
            "value": f"The anatomical structures present are: {classes_str}."
        })

        # 第三轮：询问风险评估
        conversations.append({
            "from": "human",
            "value": "What is the risk assessment for this surgical step?"
        })

        # 提取风险信息
        risk_info = ""
        if "<risk>" in response and "</risk>" in response:
            risk_start = response.find("<risk>") + len("<risk>")
            risk_end = response.find("</risk>")
            risk_info = response[risk_start:risk_end]

        risk_response = f"The risk level is {risk_level}. {risk_info}" if risk_info else f"The risk level is {risk_level}."
        conversations.append({
            "from": "gpt",
            "value": risk_response
        })

        # 第四轮：询问下一步操作
        conversations.append({
            "from": "human",
            "value": "What should be the next step in the surgery?"
        })

        # 提取下一步操作建议
        next_step = "No specific next step provided."
        if "\nNext step: " in response:
            next_step_start = response.find("\nNext step: ") + len("\nNext step: ")
            next_step = response[next_step_start:].strip()
        elif "Next: " in response:
            next_step_start = response.find("Next: ") + len("Next: ")
            next_step = response[next_step_start:].split("\n<risk>")[0].strip()

        conversations.append({
            "from": "gpt",
            "value": next_step
        })

        # 添加到结果中
        llava_format_data.append({
            "id": unique_id,
            "image": image_value,  # 使用完整路径
            "conversations": conversations
        })

    # 保存转换后的数据
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(llava_format_data, f, ensure_ascii=False, indent=2)

    print(f"转换完成，已保存到 {output_file}")



if __name__ == "__main__":
    # 输入和输出文件路径
    cholec80_file = "/media/user/data3/toky/Datasets/Cholec80QA/cholec80_qa_dataset.json"
    output_file = "/media/user/data3/toky/Datasets/Cholec80QA/converted_cholec80_to_llava.json"

    # 执行转换
    convert_to_llava_format(cholec80_file, output_file)
