import json
import base64
import re
from pathlib import Path
from PIL import Image
from io import BytesIO




def clean_image_path(image_path_str):
    """清理图像路径中的多余引号、逗号和特殊字符"""
    # 移除路径前后的引号、逗号和可能的转义字符
    cleaned = re.sub(r'^["\',]+|["\',]+$', '', image_path_str)
    # 处理可能的转义斜杠
    cleaned = cleaned.replace('\\/', '/')
    return cleaned.strip()


def image_to_base64(image_path):
    """将图像文件转换为 base64 编码字符串，增加异常处理"""
    try:
        # 检查路径是否存在
        if not Path(image_path).exists():
            print(f"图像文件不存在：{image_path}")
            return None

        # 打开图像并转换为 JPEG 格式
        with Image.open(image_path) as img:
            # 处理透明通道（若有），转换为 RGB
            if img.mode in ("RGBA", "P", "LA"):
                img = img.convert("RGB")

            # 限制图像大小，避免编码后体积过大
            max_size = (1024, 1024)
            img.thumbnail(max_size)

            # 将图像保存到内存缓冲区
            buffer = BytesIO()
            # 适当压缩，平衡质量和体积
            img.save(buffer, format="JPEG", quality=85)

            # 转换为 base64 编码
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{img_base64}"

    except Exception as e:
        print(f"图像编码失败（路径：{image_path}）：{str(e)}")
        return None


def clean_text(text):
    """清理文本中的特殊字符，避免JSON解析问题"""
    if not text:
        return ""
    # 移除控制字符（如换行、制表符等）
    cleaned = re.sub(r'[\x00-\x1F\x7F]', ' ', text)
    # 处理引号转义问题
    cleaned = cleaned.replace('"', '\\"')
    return cleaned.strip()


def generate_target_jsonl(source_data):
    """生成目标格式的JSONL数据（每行一个JSON对象）"""
    error_log = []

    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f_out:
        for item_idx, item in enumerate(source_data, 1):
            try:
                # 1. 提取并清理图像路径
                image_path_str = item.get("image", "")
                image_path = clean_image_path(image_path_str)
                if not image_path:
                    error_log.append(f"项目 {item_idx}：无效的图像路径")
                    continue

                # 2. 将图像转换为 base64 编码
                image_base64 = image_to_base64(image_path)
                if not image_base64:
                    error_log.append(f"项目 {item_idx}：图像编码失败，路径：{image_path}")
                    continue

                # 3. 提取人类的问题（从 conversations 中）
                conversations = item.get("conversations", [])
                if not conversations:
                    error_log.append(f"项目 {item_idx}：没有对话内容")
                    continue

                for conv_idx, conv in enumerate(conversations, 1):
                    try:
                        if conv.get("from") == "human" and "<image>" not in conv.get("value", ""):
                            # 清理问题文本
                            question_text = clean_text(conv.get("value", ""))
                            if not question_text:
                                continue

                            # 4. 构建目标 JSON 结构
                            target_json = {
                                "messages": [
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "text", "text": question_text},
                                            {
                                                "type": "image_url",
                                                "image_url": {"url": image_base64}
                                            }
                                        ]
                                    }
                                ]
                            }

                            # 5. 写入JSONL文件（每行一个JSON对象）
                            # 使用json.dump确保格式正确
                            json.dump(target_json, f_out, ensure_ascii=False)
                            f_out.write("\n")  # 每行一个对象

                    except Exception as e:
                        error_log.append(f"项目 {item_idx} 对话 {conv_idx} 处理失败：{str(e)}")
                        continue

            except Exception as e:
                error_log.append(f"项目 {item_idx} 整体处理失败：{str(e)}")
                continue

    # 保存错误日志
    if error_log:
        with open(ERROR_LOG_PATH, "w", encoding="utf-8") as f_err:
            for err in error_log:
                f_err.write(err + "\n")
        print(f"处理完成，共 {len(error_log)} 条错误记录，详情见：{ERROR_LOG_PATH}")

    return len(error_log)


def gen_chole_with_imageurl():
    try:
        # 加载源数据
        with open(SOURCE_JSON_PATH, "r", encoding="utf-8") as f:
            try:
                source_data = json.load(f)
                # 确保源数据是列表（若为单个对象则包装为列表）
                if not isinstance(source_data, list):
                    source_data = [source_data]
                print(f"成功加载源数据，共 {len(source_data)} 条记录")
            except json.JSONDecodeError as e:
                print(f"源数据JSON解析失败：{str(e)}")
                print("请先修复源数据文件的JSON格式错误")
                exit(1)

        # 生成目标格式数据（JSONL）
        error_count = generate_target_jsonl(source_data)

        # 统计输出文件中的记录数
        try:
            with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as f:
                line_count = sum(1 for line in f if line.strip())
            print(f"生成完成！共处理 {line_count} 条有效数据，保存至：{OUTPUT_JSON_PATH}")
            if error_count > 0:
                print(f"注意：有 {error_count} 条记录处理失败，详情见错误日志")
        except Exception as e:
            print(f"生成完成，但统计有效记录数失败：{str(e)}")
            print(f"输出文件保存至：{OUTPUT_JSON_PATH}")

    except Exception as e:
        print(f"程序运行失败：{str(e)}")
        exit(1)


def gen_chole_no_imageurl():
    try:
        # 加载源数据
        with open(SOURCE_JSON_PATH, "r", encoding="utf-8") as f:
            try:
                source_data = json.load(f)
                # 确保源数据是列表（若为单个对象则包装为列表）
                if not isinstance(source_data, list):
                    source_data = [source_data]
                print(f"成功加载源数据，共 {len(source_data)} 条记录")
            except json.JSONDecodeError as e:
                print(f"源数据JSON解析失败：{str(e)}")
                print("请先修复源数据文件的JSON格式错误")
                exit(1)

        error_log = []

        with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f_out:
            for item_idx, item in enumerate(source_data, 1):
                try:
                    # 提取对话内容
                    conversations = item.get("conversations", [])
                    if not conversations:
                        error_log.append(f"项目 {item_idx}：没有对话内容")
                        continue

                    # 成对处理对话（human -> assistant）
                    i = 0
                    while i < len(conversations) - 1:
                        try:
                            human_conv = conversations[i]
                            assistant_conv = conversations[i + 1]

                            # 检查是否为有效的对话对
                            if (human_conv.get("from") == "human" and
                                assistant_conv.get("from") == "gpt"):

                                # 清理问题和回答文本
                                question_text = clean_text(human_conv.get("value", ""))
                                answer_text = clean_text(assistant_conv.get("value", ""))

                                if question_text and answer_text:
                                    # 构建目标 JSON 结构（不包含图像）
                                    target_json = {
                                        "messages": [
                                            {
                                                "role": "user",
                                                "content": question_text
                                            },
                                            {
                                                "role": "assistant",
                                                "content": answer_text
                                            }
                                        ]
                                    }

                                    # 写入JSONL文件
                                    json.dump(target_json, f_out, ensure_ascii=False)
                                    f_out.write("\n")

                                i += 2  # 处理下一对对话
                            else:
                                i += 1

                        except Exception as e:
                            error_log.append(f"项目 {item_idx} 对话处理失败：{str(e)}")
                            i += 1
                            continue

                except Exception as e:
                    error_log.append(f"项目 {item_idx} 整体处理失败：{str(e)}")
                    continue

        # 保存错误日志
        if error_log:
            with open(ERROR_LOG_PATH, "w", encoding="utf-8") as f_err:
                for err in error_log:
                    f_err.write(err + "\n")
            print(f"处理完成，共 {len(error_log)} 条错误记录，详情见：{ERROR_LOG_PATH}")

        # 统计输出文件中的记录数
        try:
            with open(OUTPUT_JSON_PATH, "r", encoding="utf-8") as f:
                line_count = sum(1 for line in f if line.strip())
            print(f"生成完成！共处理 {line_count} 条有效数据，保存至：{OUTPUT_JSON_PATH}")
            if error_log:
                print(f"注意：有 {len(error_log)} 条记录处理失败，详情见错误日志")
        except Exception as e:
            print(f"生成完成，但统计有效记录数失败：{str(e)}")
            print(f"输出文件保存至：{OUTPUT_JSON_PATH}")

    except Exception as e:
        print(f"程序运行失败：{str(e)}")
        exit(1)



if __name__ == "__main__":
    # 源数据路径（请替换为你的实际路径）
    SOURCE_JSON_PATH = "/media/user/data3/toky/Datasets/Cholec80QA/converted_cholec80_to_llava.json"
    # 输出结果路径（JSONL格式）
    OUTPUT_JSON_PATH = "/media/user/data3/toky/Datasets/Cholec80QA/convert_to_doubao_sft_no_image.jsonl"
    # 错误日志路径
    ERROR_LOG_PATH = "/media/user/data3/toky/Datasets/Cholec80QA/convert_errors.log"
    # gen_chole_with_imageurl()
    gen_chole_no_imageurl()
