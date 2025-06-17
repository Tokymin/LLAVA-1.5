import json
from tqdm import tqdm
from llava.eval.run_llava import eval_model
from llava.mm_utils import get_model_name_from_path


def evaluate_textvqa(model_path, questions_file, image_folder, output_file):
    # 加载问题文件
    with open(questions_file, 'r') as f:
        questions_data = json.load(f)['data']

    results = []
    for item in tqdm(questions_data):
        image_id = item['image_id']
        question = item['question']
        image_path = f"{image_folder}/train_images/{image_id}.jpg"

        # 准备评估参数
        args = type('Args', (), {
            "model_path": model_path,
            "model_base": None,
            "model_name": get_model_name_from_path(model_path),
            "query": question,
            "conv_mode": None,
            "image_file": image_path,
            "sep": ",",
            "temperature": 0,
            "top_p": None,
            "num_beams": 1,
            "max_new_tokens": 128
        })()

        # 运行模型推理
        answer = eval_model(args)

        # 保存结果
        results.append({
            "question_id": item["question_id"],
            "image_id": image_id,
            "question": question,
            "answer": answer,
            "prediction": answer  # 假设模型直接输出答案
        })

    # 保存结果到文件
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    evaluate_textvqa(
        model_path="liuhaotian/llava-v1.5-7b",  # 可替换为您训练的模型路径
        questions_file="data/textvqa/TextVQA_0.5.1_val.json",
        image_folder="data/textvqa/train_val_images",
        output_file="results/textvqa_results.json"
    )
