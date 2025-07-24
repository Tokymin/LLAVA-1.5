import json
import sys
import os
import urllib
import urllib.request as ureq
import time  # 新增：用于重试间隔

download = 1  # 0 if images are already downloaded
MAX_RETRIES = 5  # 最大重试次数
RETRY_DELAY = 2  # 重试间隔（秒）

# 加载数据集（省略部分代码，与原代码一致）
with open('/mnt/share/Datasets/LLAVA-1.5/playground/data/ocr_vqa/dataset.json', 'r') as fp:
    data = json.load(fp)

if download == 1:
    # 创建目录（如果不存在，避免重复创建报错）
    img_dir = '/mnt/share/Datasets/LLAVA-1.5/playground/data/ocr_vqa/images'
    os.makedirs(img_dir, exist_ok=True)  # 替换 os.mkdir，避免目录已存在时报错

    for k in data.keys():
        ext = os.path.splitext(data[k]['imageURL'])[1]
        outputFile = os.path.join(img_dir, f'{k}{ext}')  # 更规范的路径拼接

        # 跳过已下载的文件（避免重复下载）
        if os.path.exists(outputFile) and os.path.getsize(outputFile) > 0:
            print(f'文件已存在，跳过：{outputFile}')
            continue

        # 带重试的下载逻辑
        retries = 0
        while retries < MAX_RETRIES:
            try:
                print(f'下载 {k}{ext}（第 {retries + 1} 次尝试）...')
                ureq.urlretrieve(data[k]['imageURL'], outputFile)
                print(f'下载成功：{outputFile}')
                break  # 成功则退出重试循环
            except Exception as e:
                retries += 1
                print(f'下载出错：{str(e)}，{RETRY_DELAY}秒后重试...')
                time.sleep(RETRY_DELAY)
        if retries >= MAX_RETRIES:
            print(f'达到最大重试次数，下载失败：{data[k]["imageURL"]}')
