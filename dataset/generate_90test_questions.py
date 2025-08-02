import json
import random

# 源文件路径（请确认路径正确）
SOURCE_FILE = "/media/user/data3/toky/Datasets/Cholec80QA/converted_cholec80_to_llava.json"
# 输出文件路径
OUTPUT_FILE = "/media/user/data3/toky/Datasets/Cholec80QA/generated_questions_fullpath.jsonl"
# 需要生成的条目数量
TARGET_COUNT = 90
# 问题类别列表（循环使用）
CATEGORIES = ["conv", "detail", "complex"]


def clean_image_path(image_path):
    """清理图像路径中的多余引号和逗号（保留完整路径）"""
    # 移除路径中可能存在的引号和逗号（如示例中的 "\" 和 \", ）
    cleaned_path = image_path.strip('",')
    return cleaned_path


def load_source_data(file_path):
    """加载源JSON文件数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 确保数据是列表格式（如果是单个对象则包装为列表）
            return data if isinstance(data, list) else [data]
    except json.JSONDecodeError as e:
        print(f"解析源文件失败：{e}")
        return []
    except FileNotFoundError:
        print(f"源文件不存在：{file_path}")
        return []


def collect_questions(source_data):
    """从源数据中收集所有人类提出的问题（保留完整图像路径）"""
    questions = []
    for item in source_data:
        # 提取并清理完整图像路径
        image_fullpath = clean_image_path(item.get("image", ""))
        if not image_fullpath:
            continue  # 跳过没有有效图像路径的条目

        # 提取对话中人类的问题（过滤包含<image>标记的问题）
        conversations = item.get("conversations", [])
        for conv in conversations:
            if conv.get("from") == "human" and "<image>" not in conv.get("value", ""):
                question_text = conv["value"].strip()
                if question_text:  # 确保问题不为空
                    questions.append({
                        "image": image_fullpath,  # 保留完整路径
                        "text": question_text
                    })
    return questions


def generate_output_data(questions, target_count):
    """生成目标格式的输出数据"""
    if len(questions) < target_count:
        print(f"警告：源数据中仅找到{len(questions)}个有效问题，将使用所有可用问题")
        target_count = len(questions)

    # 随机选择目标数量的问题
    selected_questions = random.sample(questions, target_count)

    # 构建输出条目
    output_data = []
    for idx, q in enumerate(selected_questions):
        # 循环分配类别
        category = CATEGORIES[idx % len(CATEGORIES)]
        output_item = {
            "question_id": idx,
            "image": q["image"],  # 完整路径
            "text": q["text"],
            "category": category
        }
        output_data.append(output_item)

    return output_data


def save_output(data, file_path):
    """保存生成的JSONL文件（每行一个JSON对象）"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for item in data:
            json.dump(item, f, ensure_ascii=False)
            f.write('\n')
    print(f"已成功生成{len(data)}条数据，保存至：{file_path}")


if __name__ == "__main__":
    source_data = load_source_data(SOURCE_FILE)
    if not source_data:
        print("无法加载源数据，程序退出")
        exit(1)

    questions = collect_questions(source_data)
    if not questions:
        print("未找到有效问题，程序退出")
        exit(1)

    output_data = generate_output_data(questions, TARGET_COUNT)
    save_output(output_data, OUTPUT_FILE)
