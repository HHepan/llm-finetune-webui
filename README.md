# llm-finetune-webui

一个用于NLP大模型微调的Web项目

├── backend/                  # FastAPI 后端
│   ├── app/
│   │   ├── api/              # 路由接口 (直接操作文件)
│   │   ├── core/             # 配置 (如定义 workspace 的绝对路径)
│   │   ├── services/         # 业务逻辑 (读写 jsonl, 启动训练进程)
│   │   └── main.py           
│   ├── scripts/              # 训练脚本
│   └── requirements.txt
|
├── webui/                 # 前端 Vue3 项目目录
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