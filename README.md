# 🚀 Local RAG Server for "Natural‑Language → SQL" (Windows 11 + WSL 2 + RTX 3060)

> **Goal** – Run a secure, local Retrieval‑Augmented Generation (RAG) service that converts natural‑language questions into MySQL 8.0 SQL using **Ollama + LangChain + Chroma**.

---

## 0. 前提条件  (Prerequisites)

| 必須                       | Version / 備考                                            |
| -------------------------- | --------------------------------------------------------- |
| Windows 11 22H2+           | GPU パススルーが安定する最新版推奨                        |
| WSL 2                      | 事前に `wsl --install -d Ubuntu-22.04` 済み               |
| NVIDIA GeForce RTX 3060    | VRAM 12 GB。Compute Capability 8.6                        |
| NVIDIA Driver **≥ 551.xx** | Windows 用 Game Ready / Studio (CUDA 12.6 世代)           |
| Docker Desktop 4.30+       | WSL 2 backend を使用 (`Settings → General → Use WSL 2 …`) |
| Python 3.10+               | `sudo apt install python3-venv`                           |

> 📝 12.6 ドライバなら CUDA 12.6 系イメージを、12.8 ドライバなら CUDA 12.8 イメージを pull してください。

---

## 1. GPU & WSL 2 動作確認

```powershell
# Windows PowerShell
nvidia-smi                       # ドライバと CUDA Version=12.6 を確認
wsl --update && wsl --shutdown   # WSL カーネルを最新化
```

```bash
# WSL (Ubuntu) 側
a) GPU が見えるか確認
$ nvidia-smi                      # GPU 一覧が出れば OK
```

---

## 2. Docker Desktop + GPU Validation

```powershell
# CUDA 12.6 系イメージ例 (ドライバ 12.6 世代に合わせる)
docker run --rm --gpus all \
  nvidia/cuda:12.6.2-base-ubuntu22.04 nvidia-smi  # GPU 情報が表示されれば OK
```

> **タグの意味** – `12.6.2-base-ubuntu22.04` = CUDA 12.6.2 + 最小 OS イメージ。ドライバも 12.6 系なら互換性 OK。

---

## 3. Ollama インストール & モデル取得

```bash
# Ubuntu (WSL) 側 – GPU を自動検知
curl -fsSL https://ollama.com/install.sh | sh      # 🗒️ インストーラ
ollama pull llama3:8b                              # 約 4.6 GB / 3 分ほど
ollama run llama3                                  # 試し起動 (Ctrl+C で終了)
```

---

## 4. Python 仮想環境 & 依存ライブラリ

```bash
sudo apt update && sudo apt install -y python3-venv build-essential
python3.10 -m venv rag-env && source rag-env/bin/activate

# requirements
pip install --upgrade \
    langchain-core langchain-community langchain-text-splitters \
    chromadb sentence-transformers ollama \
    fastapi \
    'uvicorn[standard]'
```

| ライブラリ                   | 役割                                              |
| ---------------------------- | ------------------------------------------------- |
| **langchain‑core/community** | RAG パイプライン実装                              |
| **langchain‑text‑splitters** | DDL をテーブル単位に分割                          |
| **chromadb**                 | ベクトル DB (ローカル)                            |
| **sentence‑transformers**    | 小型埋め込みモデル呼び出し                        |
| **ollama**                   | Python からローカル LLM を呼ぶラッパー            |
| **fastapi**                  | Python で API を開発するための Web フレームワーク |
| **uvicorn[standard]**        | FastAPI 起動用                                    |

---

## 5. DDL インデックス化

```bash
mkdir scripts && cd scripts
nano index_ddl.py     # 下記スクリプトを貼り付け (Ctrl+O, Ctrl+X で保存)
python index_ddl.py   # → Indexed xx chunks と出たら成功
```

```python
"""index_ddl.py – CREATE TABLE 群をベクトル化 (要: schema/all_tables.sql)"""
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OllamaEmbeddings
from chromadb import Client

DDL = "../schema/all_tables.sql"  # DDL ファイルパス
text = Path(DDL).read_text()

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800, chunk_overlap=0, separators=["CREATE TABLE", ";"],
)
docs = splitter.create_documents([text])

embed = OllamaEmbeddings(model="nomic-embed-text")
chroma = Client().create_collection("ddl")

for i, d in enumerate(docs):
    chroma.add(ids=[f"ddl_{i}"], documents=[d.page_content],
               embeddings=[embed.embed_query(d.page_content)],
               metadatas=[{"table_idx": i}])
print(f"Indexed {len(docs)} chunks")
```

---

## 6. FastAPI で RAG サーバ起動

```bash
# app.py を作成
nano app.py
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2  # 起動
```

> `app.py` のサンプルコードは `docs/app.py.sample` を参照 (README 上部に貼ったものと同等)。

### 動作テスト

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "30歳以上の社員IDと名前を取得"}' | jq
```

出力例:

```json
{
  "sql": "SELECT employee_id, name FROM employees WHERE age >= 30;",
  "ddl_context": "CREATE TABLE `employees` …"
}
```

---

## 7. よく使うメンテコマンド (コメント付き)

```bash
# GPU 使用率確認
watch -n 1 nvidia-smi        # 1秒ごとに利用状況を確認

# Ollama モデル一覧
ollama list                  # 全 Pull 済みモデル

# DDL 更新 → 再インデックス (CI で自動化推奨)
python scripts/index_ddl.py

# RAG サーバをバックグラウンドで起動 (tmux)
tmux new -s rag "uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2"
```

---

> © 2025 – Internal use only. Powered by Ollama, LangChain, Chroma, FastAPI.
