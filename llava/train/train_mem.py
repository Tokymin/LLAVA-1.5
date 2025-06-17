import sys
import os
from llava.train.train import train
# 获取当前脚本所在目录
script_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录（假设train.py在项目根目录下的llava/train目录中）
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))

# 将项目根目录添加到Python搜索路径
sys.path.insert(0, project_root)


if __name__ == "__main__":
    train(attn_implementation="flash_attention_2")
