import torch

from llava.constants import IMAGE_TOKEN_INDEX, DEFAULT_IMAGE_TOKEN
from llava.conversation import conv_templates, SeparatorStyle
from llava.model.builder import load_pretrained_model
from llava.utils import disable_torch_init
from llava.mm_utils import tokenizer_image_token
from transformers.generation.streamers import TextIteratorStreamer

from PIL import Image

import requests
from io import BytesIO
# # 从 cog 框架导入用于构建预测器、输入定义等相关类和工具
from cog import BasePredictor, Input, Path, ConcatenateIterator
import time
import subprocess
from threading import Thread

import os

os.environ["HUGGINGFACE_HUB_CACHE"] = os.getcwd() + "/weights"
# # 设置 Hugging Face Hub 缓存目录为当前工作目录下的 weights 文件夹
# url for the weights mirror 权重镜像的基础 URL
REPLICATE_WEIGHTS_URL = "https://weights.replicate.delivery/default"
# files to download from the weights mirrors # 定义需要从权重镜像下载的模型权重及相关文件信息，包含不同模型仓库（dest）、对应镜像路径（src）和要下载的文件列表（files）
weights = [
    {
        "dest": "liuhaotian/llava-v1.5-13b",
        # git commit hash from huggingface
        "src": "llava-v1.5-13b/006818fc465ebda4c003c0998674d9141d8d95f8",
        "files": [
            "config.json",
            "generation_config.json",
            "pytorch_model-00001-of-00003.bin",
            "pytorch_model-00002-of-00003.bin",
            "pytorch_model-00003-of-00003.bin",
            "pytorch_model.bin.index.json",
            "special_tokens_map.json",
            "tokenizer.model",
            "tokenizer_config.json",
        ]
    },
    {
        "dest": "openai/clip-vit-large-patch14-336",
        "src": "clip-vit-large-patch14-336/ce19dc912ca5cd21c8a653c79e251e808ccabcd1",
        "files": [
            "config.json",
            "preprocessor_config.json",
            "pytorch_model.bin"
        ],
    }
]


# 从指定 URL 下载 JSON 文件到目标路径
def download_json(url: str, dest: Path):
    res = requests.get(url, allow_redirects=True)
    if res.status_code == 200 and res.content:
        with dest.open("wb") as f:
            f.write(res.content)
    else:
        print(f"Failed to download {url}. Status code: {res.status_code}")


# 从权重镜像下载指定模型的相关文件到本地目标路径
def download_weights(baseurl: str, basedest: str, files: list[str]):
    basedest = Path(basedest)
    start = time.time()
    print("downloading to: ", basedest)
    basedest.mkdir(parents=True, exist_ok=True)  # 创建目标目录（含父目录）
    for f in files:
        dest = basedest / f
        url = os.path.join(REPLICATE_WEIGHTS_URL, baseurl, f)
        if not dest.exists():  # 文件不存在时才下载
            print("downloading url: ", url)
            if dest.suffix == ".json":  # JSON 文件调用专门方法下载
                download_json(url, dest)
            else:
                subprocess.check_call(["pget", url, str(dest)], close_fds=False)
    print("downloading took: ", time.time() - start)

# 预测器类，用于加载模型和执行预测
class Predictor(BasePredictor):
    def setup(self) -> None:
        """Load the model into memory to make running multiple predictions efficient"""
        """加载模型到内存，以便高效执行多次预测"""
        for weight in weights:  # 遍历权重配置，下载所需模型文件
            download_weights(weight["src"], weight["dest"], weight["files"])
        disable_torch_init() # 禁用 PyTorch 的初始化（可能为了自定义初始化或加速）
        # 加载预训练模型，这里指定加载 liuhaotian/llava-v1.5-13b 模型
        self.tokenizer, self.model, self.image_processor, self.context_len = load_pretrained_model(
            "/mnt/share/HuggingfaceModels/liuhaotian/llava-v1.5-7b", model_name="llava-v1.5-13b", model_base=None, load_8bit=False, load_4bit=False)

    def predict(
        self,
        image: Path = Input(description="Input image"),
        prompt: str = Input(description="Prompt to use for text generation"),
        top_p: float = Input(
            description="When decoding text, samples from the top p percentage of most likely tokens; lower to ignore less likely tokens",
            ge=0.0, le=1.0, default=1.0),
        temperature: float = Input(
            description="Adjusts randomness of outputs, greater than 1 is random and 0 is deterministic", default=0.2,
            ge=0.0),
        max_tokens: int = Input(description="Maximum number of tokens to generate. A word is generally 2-3 tokens",
                                default=1024, ge=0),
    ) -> ConcatenateIterator[str]:
        """Run a single prediction on the model"""
        """在模型上执行单次预测"""
        conv_mode = "llava_v1"# 对话模板模式；对话模板定义了人机交互时的格式规范，包括角色标识（如 “用户”“助手”）、对话分隔符、图像标记插入位置等。
        conv = conv_templates[conv_mode].copy() # 获取并复制对应对话模板

        image_data = load_image(str(image))# 加载图像数据
        image_tensor = self.image_processor.preprocess(image_data, return_tensors='pt')['pixel_values'].half().cuda()
        # 预处理图像，转换为模型需要的张量形式（半精度、cuda 设备）
        # loop start
        # 构建对话内容，将图像标记和提示词组合
        # just one turn, always prepend image token
        inp = DEFAULT_IMAGE_TOKEN + '\n' + prompt
        conv.append_message(conv.roles[0], inp)# 添加用户消息

        conv.append_message(conv.roles[1], None)# 预留助手消息位置
        prompt = conv.get_prompt()# 获取完整对话提示词
        # 处理提示词，转换为模型可输入的张量形式（包含图像标记处理）
        input_ids = tokenizer_image_token(prompt, self.tokenizer, IMAGE_TOKEN_INDEX, return_tensors='pt').unsqueeze(
            0).cuda()
        # 确定停止标记，用于判断生成何时结束
        stop_str = conv.sep if conv.sep_style != SeparatorStyle.TWO else conv.sep2
        keywords = [stop_str]
        # 文本流生成器，用于流式获取生成的文本
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, timeout=20.0)

        with torch.inference_mode(): # 推理模式（禁用梯度计算，节省内存和加速）
            # 启动线程执行模型生成，将结果通过 streamer 流式输出
            thread = Thread(target=self.model.generate, kwargs=dict(
                inputs=input_ids,
                images=image_tensor,
                do_sample=True, # 启用采样，配合 temperature 等控制随机性
                temperature=temperature,
                top_p=top_p,
                max_new_tokens=max_tokens,
                streamer=streamer,
                use_cache=True)) # 启用采样，配合 temperature 等控制随机性
            thread.start()
            # 处理流式输出的文本，做一些格式化处理（处理空格、停止标记等）
            # workaround: second-to-last token is always " "
            # but we want to keep it if it's not the second-to-last token
            prepend_space = False
            for new_text in streamer:
                if new_text == " ":
                    prepend_space = True
                    continue
                if new_text.endswith(stop_str):
                    new_text = new_text[:-len(stop_str)].strip()
                    prepend_space = False
                elif prepend_space:
                    new_text = " " + new_text
                    prepend_space = False
                if len(new_text):# 有实际内容时才 yield 输出
                    yield new_text
            if prepend_space:
                yield " "
            thread.join() # 等待生成线程结束

# 加载图像，支持从 URL 或本地路径加载
def load_image(image_file):
    if image_file.startswith('http') or image_file.startswith('https'):
        response = requests.get(image_file)
        image = Image.open(BytesIO(response.content)).convert('RGB')
    else:
        image = Image.open(image_file).convert('RGB')
    return image
