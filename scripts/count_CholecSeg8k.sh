#!/bin/bash

# 定义目标目录
TARGET_DIR="/media/user/data3/toky/Datasets/CholecSeg8k/"

# 检查目录是否存在
if [ ! -d "$TARGET_DIR" ]; then
    echo "错误：目录 $TARGET_DIR 不存在！"
    exit 1
fi

# 统计以_endo.png结尾的文件数量
# 使用find命令递归查找，-type f确保只统计文件，-name指定文件名模式
file_count=$(find "$TARGET_DIR" -type f -name "*_endo.png" | wc -l)

# 输出结果
echo "在目录 $TARGET_DIR 及其子目录中："
echo "以_endo.png结尾的图像文件总数为：$file_count"
