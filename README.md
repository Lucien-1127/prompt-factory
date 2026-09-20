# 提示詞工廠 v11.1.0

把需求整理成可重複使用、可直接複製且有明確驗收條件的提示詞。支援討論、生成、優化、評估；依任務載入圖片／影片、工具代理或多代理規格。

## 使用入口

將完整目錄放入支援此格式的技能環境，由 `SKILL.md` 載入。需要建立寫手系統指令時，使用獨立的 `writer-compiler`。只要求直接寫文章、翻譯或修程式時，不進入提示詞製作流程。

一般任務採最小足夠結構；需要自主迭代時，才加入權限、成本、狀態、失敗復原與停止條件。產出的提示詞不代表工具已連接或任務已執行。

## 套件內容

| 檔案 | 用途 |
| --- | --- |
| `SKILL.md` | 動作路由、任務分級與統一交付契約 |
| `references/templates.md` | 提示詞骨架 |
| `references/session-kernel.md` | 視覺媒體規格 |
| `references/agent-runtime-contract.md` | 有界迴圈、狀態與停止條件 |
| `references/tool-contract.md` | 工具與目標平台能力契約 |
| `references/orchestration.md` | 多代理分工與交接 |
| `references/evaluation-security.md` | 評測、安全與證據分級 |
| `agents/openai.yaml`、`assets/icon.svg` | 技能介面中繼資料與圖示 |
| `scripts/`、`evals/behavior-cases.json` | 靜態檢查器、回歸測試及行為案例 |

## 版本同步

2026-09-20：同步目前已安裝的 v11.1.0 完整技能內容。舊入口使用通用能力容器規格，指向本儲存庫未提供的 `capabilities/`、`instructions/` 與 `runtime/`；本次將入口宣告對齊實際檔案。舊內容保留於 Git 版本歷史。

## 驗證

在 Linux／WSL 的 Python 環境執行（需 PyYAML）：

```bash
python3 scripts/validate_prompt_factory.py
python3 scripts/test_validate_prompt_factory.py
```

靜態結構與測試通過，不代表模型行為、真實工具呼叫或付費 API 已驗收。行為案例是待實測規格，不可當成已執行結果。
