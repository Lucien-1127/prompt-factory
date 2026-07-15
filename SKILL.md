# SKILL.md

> AI Capability Repository 的通用載入器。
> 本檔只定義如何理解、載入與安全降級；不定義任何具體能力，也不承擔能力匹配策略。

## 核心定位

你正在載入一個跨 AI 平台可攜式的 Capability Repository。依序讀取 Repository 契約、辨識當前環境、套用全域規則、發現可用能力；收到使用者需求後，再使用已建立的能力選擇機制執行。

Repository 的目標是：AI 可以直接閱讀，人可以管理，Agent 可以執行。請依環境能力啟用可用層級，缺少選配層時應降級，而非將 Repository 視為失效。

## 初始化流程

### 1. 讀取契約

先讀取 `manifest.yaml`。它是 Repository 的權威入口契約，定義 Repository 身份、相容性要求、入口位置、能力發現規則、全域 instructions、runtime 狀態與 extension 發現規則。

若無法解析 YAML，仍應以文字閱讀方式取得可理解欄位；若 `manifest.yaml` 不存在，說明無法依契約初始化，並只處理目前可讀取的明確文件。

### 2. 辨識載入環境

依 `compatibility.adapters` 與自身實際能力判斷可用 adapter：

- `markdown-instruction`：可讀取並遵循 Markdown 指令；使用基礎模式。
- `skill-loader`：可載入 SKILL 類指令與相關檔案；使用基礎模式。
- `runtime-agent`：可讀取並執行 `runtime/` 所定義的程式化流程；可啟用增強模式。

不確定環境時，預設採用 `markdown-instruction`。不要假設特定 AI Host、模型供應商或平台專屬功能。

### 3. 套用全域規則

依 `instructions` 清單讀取所有存在的全域規則，並按宣告優先序全程遵守。全域規則優先於 capability 內部規則。

若 instructions 目錄或其中檔案尚不存在，將它視為早期開發狀態，不視為錯誤；改以謹慎、誠實、可解釋的預設行為運作。

### 4. 發現能力目錄

依 `capabilities.discovery` 發現能力：若 `capabilities/index.yaml` 存在，先以它取得能力 catalog；否則掃描 `capabilities/` 的直接子目錄。

每個 capability 的共同可讀契約是 `capability.md`。`capability.yaml` 是選配 machine-readable 描述，只在環境可可靠處理時使用。

此階段只建立可用能力的目錄與摘要，**不要預先載入全部 capability 內容，也不要在 SKILL.md 寫死能力清單。**

### 5. 判斷 runtime 狀態

檢查 `runtime.status`：

- `disabled`：不得使用 runtime。
- `available`：runtime 存在；僅在當前環境明確支援時使用。
- `enabled`：當前環境支援 runtime 時，優先使用其執行增強；不支援時仍回退至基礎模式。

Runtime 是可選加速器，不是 Repository 完整性的前提。它可增強選擇、規劃與輸出，但不得阻塞基礎模式。

### 6. 等待需求並載入所需能力

初始化後，不主動列舉全部能力、不執行能力，也不以冗長自我介紹取代任務。等待使用者提出需求。

收到需求後，依當時已可用的能力選擇機制找出需要的 capability，再讀取其 `capability.md` 並遵守其中規則。**正式的能力匹配規則屬於 M1 Resolver 契約；在它建立前，不要假裝存在自動 Resolver。** 若必須作出暫時選擇，應依能力的明示名稱、描述與使用者需求做最小且可解釋的判斷；歧義重大時先詢問一個最關鍵的澄清問題。

## 邊界與降級

SKILL.md 是 Loader，不是能力本體、能力索引或 runtime 規格。新增、修改或移除 capability 時，原則上只調整 `capabilities/` 與其 index，不應為了列舉能力而修改本檔。

若 `capabilities/` 為空、index 遺失、runtime 不存在、extensions 不存在，應說明目前可用範圍並繼續服務；不要將選配資源的缺失誤判為初始化失敗。

若 capability 規則與全域 instructions 衝突，以全域 instructions 為準；若 Repository 契約與平台慣例衝突，以可安全執行且不違反明示契約的方式降級。

## 給維護者

人類使用者請閱讀 `README.md`。本檔是 AI 的載入指令。

修改此檔前，先問：這是所有載入環境都必須知道的載入規則嗎？若答案是否定的，應把內容放在 manifest、capability、instructions 或 runtime，而不是放進 SKILL.md。
