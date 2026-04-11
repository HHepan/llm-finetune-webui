# llm-finetune-webui

一个用于NLP大模型微调的Web项目
```
├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/              # 路由接口 (直接操作文件)
│   │   ├── core/             # 配置 (如定义 workspace 的绝对路径)
│   │   ├── services/         # 业务逻辑 (读写 jsonl, 启动训练进程)
│   │   └── main.py           
│   ├── scripts/              # 训练脚本
│   └── requirements.txt
|
├── webui/                 # 前端 Vue3 项目目录s
│   ├── src/
│   │   ├── api/              # Axios 请求封装
│   │   ├── assets/           # 静态资源
│   │   ├── components/       # 公共组件
│   │   ├── router/           # 路由配置 (数据管理、微调训练、对话测试)
│   │   ├── views/            # 页面视图 (DataManage.vue, Train.vue, Chat.vue)
│   │   └── App.vue
│   └── package.json
│
└── workspace/                # 你的核心工作区 (直接扫描这里)
    ├── data/                 # 存放 .jsonl 数据集
    ├── base_models/          # 存放下载的基底模型 (如 Qwen-7B-Chat)
    └── checkpoints/          # 存放训练输出目录 (包含权重和 trainer_state.json)
```
```
启动测试
# 终端1 - 后端
cd backend
conda install --yes --file requirements.txt
uvicorn app.main:app --reload --port 8000
# 终端2 - 前端  
cd web
npm install
npm run dev
```
```
启动微调训练（基于目录 llm-finetune-webui/ 的操作）
cd workspace/tools/

[ ! -d "RWKV-PEFT" ] && git clone https://gitee.com/rwkv-vibe/RWKV-PEFT.git

cd RWKV-PEFT/ && pip install -r requirements.txt

mkdir ./json2binidx_tool/data/ && cp ../../data/out/total_data.jsonl ./json2binidx_tool/data/

python3 ./json2binidx_tool/tools/preprocess_data.py --input ./json2binidx_tool/data/total_data.jsonl --output-prefix ./json2binidx_tool/data/total_data --vocab ./json2binidx_tool/rwkv_vocab_v20230424.txt --dataset-impl mmap --tokenizer-type RWKVTokenizer --append-eod && mv ./json2binidx_tool/data/total_data_text_document.bin ./json2binidx_tool/data/total_data.bin && mv ./json2binidx_tool/data/total_data_text_document.idx ./json2binidx_tool/data/total_data.idx

sh scripts/lora.sh
```
```
RWKV-PEFT/rwkvt/lightning_train/trainer.py => on_train_epoch_end 方法

原代码（167-170行）：
def on_train_epoch_end(self, trainer, pl_module):
    args = self.args
    if (trainer.is_global_zero):

新代码（167-173行）：
def on_train_epoch_end(self, trainer, pl_module):
    args = self.args
    current_epoch = args.epoch_begin + trainer.current_epoch
    should_save = (current_epoch + 1) % args.epoch_save == 0
    if (trainer.is_global_zero) and should_save:

原代码（179行）路径变量：
merged_path = f"{args.proj_dir}/rwkv-{args.epoch_begin + trainer.current_epoch}.pth"

新代码（182行）路径变量：
merged_path = f"{args.proj_dir}/rwkv-{current_epoch}.pth"

cp RWKV-PEFT/rwkvt/lightning_train/trainer.py RWKV-PEFT/rwkvt/lightning_train/trainer.py.bak

sed -i '167,170c\def on_train_epoch_end(self, trainer, pl_module):\n    args = self.args\n    current_epoch = args.epoch_begin + trainer.current_epoch\n    should_save = (current_epoch + 1) % args.epoch_save == 0\n    if (trainer.is_global_zero) and should_save:' RWKV-PEFT/rwkvt/lightning_train/trainer.py

sed -i '179c\    merged_path = f"{args.proj_dir}/rwkv-{current_epoch}.pth"' RWKV-PEFT/rwkvt/lightning_train/trainer.py
```
