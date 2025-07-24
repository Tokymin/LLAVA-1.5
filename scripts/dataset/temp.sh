#!/bin/bash

# 定义源目录和目标目录
SOURCE_DIR="/mnt/share/Datasets/LLAVA-1.5/playground/data/vg/VG_100K_2/images2/VG_100K_2"
DEST_DIR="/mnt/share/Datasets/LLAVA-1.5/playground/data/vg/VG_100K_2/"

# 检查源目录是否存在
if [ ! -d "$SOURCE_DIR" ]; then
    echo "错误：源目录 $SOURCE_DIR 不存在！"
    exit 1
fi

# 检查目标目录是否存在，不存在则创建
if [ ! -d "$DEST_DIR" ]; then
    echo "目标目录 $DEST_DIR 不存在，正在创建..."
    mkdir -p "$DEST_DIR"
    if [ $? -ne 0 ]; then
        echo "错误：创建目标目录 $DEST_DIR 失败！"
        exit 1
    fi
fi

# 移动源目录下的所有图片文件到目标目录
# 这里假设图片文件的扩展名为常见的.jpg、.jpeg、.png、.gif、.bmp
echo "正在将 $SOURCE_DIR 下的图片移动到 $DEST_DIR ..."
find "$SOURCE_DIR" -maxdepth 1 -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.gif" -o -iname "*.bmp" \) -exec mv {} "$DEST_DIR/" \;

# 检查移动操作是否成功
if [ $? -eq 0 ]; then
    echo "图片移动完成！"
else
    echo "错误：图片移动过程中出现问题！"
    exit 1
fi
