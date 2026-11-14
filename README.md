# 湾区融桥 GBA Bridge Finance

跨境贸易金融智能分析与产品推荐系统

**AI 辅助分析，不构成信贷审批；正式申请、合规审查、风险评估与最终授信由 ICBC 按现有流程完成。**

---

## 系统概述

本系统面向大湾区跨境经营中小企业，提供从单据上传到金融产品推荐的全流程 AI 辅助分析：

```
单据上传 → OCR → 文档理解 → 结构化交易数据 → 交易关系图谱
→ 风险规则引擎 → 多币种现金流预测 → 情景模拟
→ 融资需求识别 → ICBC 产品匹配 → RM 工作台 → 人工复核 → 交易后监控
```

### 边界声明（贯穿全平台）

- 平台只做分析、预测、匹配、推荐和 RM 协作支持
- **不自动批贷、不自动定额度、不直接执行金融交易、不替代 KYC/AML/信用评估/最终审批**
- 高风险交易 100% 进入人工复核：Flag → Escalate → RM Review
- 所有金额、汇率、日期为演示假设，界面标注 "Illustrative assumptions"

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 16 + TypeScript + Tailwind CSS 4 + ECharts |
| 后端 | FastAPI (Python) + SQLAlchemy + Uvicorn |
| 数据库 | SQLite（schema 兼容 PostgreSQL） |
| OCR | Tesseract + pdfplumber + PyMuPDF + openpyxl（支持 PDF/图片/Excel） |
| RAG | 内置关键词检索知识库（离线可演示） |
| 图谱 | Canvas 渲染交易关系图 |

---

## 目录结构

```
bridge-finance/
├── index.html                  ← 概念展示首页（保留原有视觉风格）
├── gba-bridge-finance.html     ← index.html 副本
├── README.md                   ← 本文件
├── backend/                    ← FastAPI 后端
│   ├── requirements.txt        ← Python 依赖清单
│   ├── gba_bridge_finance.db   ← SQLite 数据库（自动生成）
│   ├── uploads/                ← 上传文件存储
│   └── app/
│       ├── __init__.py
│       ├── models.py           ← 数据库模型（16 张表）
│       ├── seed.py             ← 种子数据（企业、交易、产品、文档）
│       ├── main.py             ← FastAPI 应用 + 全部 API 路由
│       └── services/
│           ├── __init__.py
│           ├── ocr_service.py       ← OCR 文字识别与字段提取
│           ├── doc_understanding.py ← 文档分类、统一数据结构、跨文档验证
│           ├── risk_engine.py       ← 5 类风险规则引擎
│           ├── cashflow_service.py  ← 多币种现金流预测与情景模拟
│           └── product_matcher.py   ← 金融产品匹配引擎 + SimpleRAG
├── frontend/                   ← Next.js 前端
│   ├── package.json
│   ├── next.config.ts          ← API 代理配置 (→ localhost:8000)
│   ├── lib/api.ts              ← API 调用辅助 + 类型定义
│   ├── components/
│   │   ├── BoundaryBanner.tsx  ← AI 治理边界声明组件
│   │   └── Navigation.tsx      ← 导航栏组件
│   └── app/
│       ├── layout.tsx
│       ├── page.tsx            ← 概念首页（含应用入口）
│       ├── app/                ← 企业端
│       │   ├── layout.tsx
│       │   ├── dashboard/      ← 企业端首页
│       │   ├── documents/      ← 单据上传与 OCR
│       │   ├── graph/          ← 交易关系图谱
│       │   ├── cashflow/       ← 现金流与情景模拟
│       │   └── report/         ← 融资预评估报告
│       ├── rm/
│       │   └── dashboard/      ← RM 工作台
│       └── monitoring/         ← 监控与告警
└── docs/
    └── demo-guide.md           ← 演示脚本
```

---

## 快速启动

### 前提条件

- Python 3.12+（推荐 3.14）
- Node.js 18+（推荐 v24）
- npm

### 1. 启动后端

```bash
cd backend

# 安装 Python 依赖（首次）
pip install fastapi uvicorn sqlalchemy pydantic pillow pytesseract pdfplumber pymupdf openpyxl numpy python-multipart

# 启动后端服务器（自动初始化 SQLite 数据库和种子数据）
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

后端启动后：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health
- 数据库文件 `gba_bridge_finance.db` 自动生成并填充种子数据

### 2. 启动前端

```bash
cd frontend

# 安装 npm 依赖（首次）
npm install

# 启动开发服务器
npm run dev
```

前端启动后：http://localhost:3000

### 3. 一键启动（Windows PowerShell）

```powershell
# 终端 1 - 后端
cd backend; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 终端 2 - 前端
cd frontend; npm run dev
```

---

## 演示账号

系统内置 4 个演示账号，无需注册直接使用（登录页暂未实现，直接访问路由即可）：

| 角色 | 用户名 | 密码 | 可访问路由 |
|------|--------|------|-----------|
| 企业用户（利丰贸易） | `enterprise` | `demo123` | `/app/*` |
| 企业用户（深圳科创） | `enterprise2` | `demo123` | `/app/*` |
| 客户经理 (RM) | `rm` | `demo123` | `/rm/dashboard` |
| 风险管理 | `risk` | `demo123` | `/rm/dashboard` |

> 注：当前版本未强制登录，所有页面可直接访问。登录 API 已实现（`POST /api/auth/login`），可后续集成。

---

## 演示步骤

### 完整端到端演示流程

#### 步骤 1：企业端首页

1. 访问 http://localhost:3000 → 概念首页
2. 点击"进入应用" → 企业端 Dashboard (`/app/dashboard`)
3. 切换企业（利丰贸易 / 深圳科创），查看交易概览

#### 步骤 2：单据上传与 OCR

1. 进入 `/app/documents`
2. 选择交易 `TX-A-001` 或 `TX-B-001`
3. 查看已上传单据的 OCR 结果：
   - 文档类型识别（Purchase Order / Sales Contract / Commercial Invoice / Payment Schedule）
   - 字段提取（Buyer、Seller、Supplier、Amount、Currency、Date 等）
   - 每字段置信度（绿条 >85%，黄条 <85% 需确认）
4. 点击"确认字段"模拟 RM 确认低置信度字段
5. 上传新文件测试 OCR（支持 PDF/图片/Excel）

#### 步骤 3：交易关系图谱

1. 进入 `/app/graph`
2. 查看交易实体关系图（企业 → 客户 → 供应商 → 单据 → 银行账户 → 物流）
3. 点击节点查看详情
4. 查看交易完整度评分和风险维度

#### 步骤 4：现金流与情景模拟

1. 进入 `/app/cashflow`
2. 查看多币种现金流时间线（ECharts 柱状图）
3. 查看资金缺口分析（Funding Gap：币种、金额、持续时间、原因）
4. 查看 5 个情景模拟结果：
   - Base Case（基准）
   - Customer Delay +15 days（客户延迟 15 天）
   - CNY Appreciation +3%（人民币升值 3%）
   - Supplier Early Payment（供应商提前付款）
   - Combined Stress Case（综合压力情景）
5. 点击"运行风险分析"查看风险规则引擎输出：
   - 交易完整度评分（0-100）
   - 5 类风险维度（Document Consistency / Missing Information / Duplicate Financing / Payment Account Change / FX Exposure）
   - 每条告警可展开 Why（Main Factors + Positive Factors + 解释）

#### 步骤 5：融资预评估报告

1. 进入 `/app/report`
2. 点击"生成报告"
3. 查看标准化报告：
   - 企业信息、交易信息
   - 完整度评分、风险维度
   - 资金需求分析（缺口、情景摘要）
   - 金融服务推荐（产品、额度、期限、用途、所需材料、知识库来源）
   - AI 分析摘要
   - RM 审核要求

#### 步骤 6：RM 工作台

1. 进入 `/rm/dashboard`
2. 查看所有交易概览（完整度、风险、缺口、推荐、缺失文档、AI 摘要）
3. 选择交易查看详情
4. 查看 AI 摘要、风险告警、产品推荐
5. 执行 RM 操作：
   - 确认 AI 提取信息
   - 编辑信息
   - 要求补充单据
   - 添加风险评论
   - 联系企业
   - 确认金融服务
   - 提交正式流程
6. 查看审计日志（底部）

#### 步骤 7：监控与告警

1. 进入 `/monitoring`
2. 查看交易后监控事件时间线：
   - 物流更新（shipment_update）
   - 汇率变动（fx_change）
   - 收款状态（payment_overdue）
3. 按严重程度筛选（全部 / 严重 / 警告 / 信息）

---

## 内置演示案例

### 案例 A：香港贸易商（TX-A-001）

| 维度 | 值 |
|------|-----|
| 企业 | 利丰贸易（香港）有限公司 |
| 买家 | ABC International LLC (USA) |
| 供应商 | Shenzhen ABC Electronics Co., Ltd. |
| 订单金额 | USD 500,000 |
| 供应商发票 | CNY 3,600,000 |
| 付款日期 | 2026-10-15（订单后 15 天付供应商） |
| 收款日期 | 2026-12-20（订单后 75 天收客户款） |
| 资金缺口 | CNY 3,600,000，持续 66 天 |
| 完整度 | 88/100 |
| 整体风险 | Medium |
| FX Exposure | High |

### 案例 B：大型供应链企业（TX-B-001）

| 维度 | 值 |
|------|-----|
| 企业 | 利丰贸易（香港）有限公司 |
| 买家 | Global Brands Inc. (USA) |
| 供应商 | Dongguan XYZ Manufacturing Co., Ltd. |
| 订单金额 | USD 5,000,000 |
| 供应商发票 | CNY 30,000,000 |
| 付款日期 | 2026-09-15 |
| 收款日期 | 2026-11-24（付款后 70 天收款） |
| 资金缺口 | CNY 30,000,000，持续 70 天 |
| 完整度 | 88/100 |
| 整体风险 | Medium |
| FX Exposure | High |
| Peak Funding Gap | CNY 30,000,000 |

---

## 数据库表

| 表名 | 说明 |
|------|------|
| enterprises | 企业档案 |
| users | 用户（企业用户/RM/风险团队） |
| documents | 上传文档 |
| ocr_fields | OCR 提取字段（含置信度） |
| transactions | 交易记录 |
| transaction_entities | 交易实体（企业/客户/供应商/账户/物流/融资） |
| transaction_links | 交易实体关系 |
| risk_alerts | 风险告警 |
| cashflow_items | 现金流条目 |
| scenarios | 情景模拟 |
| funding_gaps | 资金缺口 |
| products | ICBC 产品知识库 |
| recommendations | 产品推荐 |
| reviews | RM 审核记录 |
| monitoring_events | 监控事件 |
| audit_logs | 审计日志 |

---

## API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/login` | 登录 |
| GET/POST | `/api/enterprises` | 企业列表/创建 |
| GET | `/api/enterprises/{id}` | 企业详情 |
| POST | `/api/documents/upload` | 上传文档（含 OCR） |
| GET | `/api/documents` | 文档列表 |
| GET | `/api/documents/{id}` | 文档详情 |
| POST | `/api/documents/{id}/ocr` | 重新 OCR |
| POST | `/api/documents/{id}/confirm` | 确认 OCR 字段 |
| GET | `/api/transactions` | 交易列表 |
| GET | `/api/transactions/{id}` | 交易详情 |
| GET | `/api/transactions/{id}/graph` | 交易关系图谱 |
| POST | `/api/risk/analyze` | 风险分析 |
| POST | `/api/cashflow/forecast` | 现金流预测 |
| POST | `/api/scenarios/simulate` | 情景模拟 |
| GET | `/api/recommendations` | 产品推荐列表 |
| POST | `/api/recommendations/generate` | 生成推荐 |
| POST | `/api/reports/preassessment` | 预审报告 |
| POST | `/api/rm/review` | RM 审核操作 |
| GET | `/api/rm/dashboard` | RM 仪表盘 |
| GET | `/api/monitoring/events` | 监控事件 |
| GET | `/api/audit/logs` | 审计日志 |
| GET | `/api/products` | 产品知识库 |
| GET | `/api/boundary` | 边界声明 |
| GET | `/api/health` | 健康检查 |

完整 API 文档：http://localhost:8000/docs

---

## ICBC 产品知识库

内置 6 类金融产品：

| 代码 | 产品 | 适用阶段 |
|------|------|---------|
| TF001 | Trade / Order Financing（贸易/订单融资） | Order, Procurement |
| CBR002 | Cross-border RMB Settlement（跨境人民币结算） | Procurement, Collection |
| RF003 | Receivables Finance / Factoring（应收账款融资/保理） | Shipment, Receivable |
| FX004 | FX Settlement / Risk Management（外汇结算/风险管理） | Procurement, Shipment, Receivable, Collection |
| GR005 | Guarantee Services（担保服务） | Order, Procurement, Shipment |
| WC006 | Working Capital Financing（流动资金贷款） | Procurement, Shipment, Receivable |

---

## 页面路由

| 路由 | 说明 |
|------|------|
| `/` | 概念首页（应用入口） |
| `/app/dashboard` | 企业端首页 |
| `/app/documents` | 单据上传与 OCR |
| `/app/graph` | 交易关系图谱 |
| `/app/cashflow` | 现金流与情景模拟 |
| `/app/report` | 融资预评估报告 |
| `/rm/dashboard` | RM 工作台 |
| `/monitoring` | 监控与告警 |

---

## 验收指标

| 指标 | 目标 |
|------|------|
| OCR 识别准确率 | ≥95% |
| 文档分类准确率 | ≥95% |
| 关键字段提取准确率 | ≥90% |
| 跨文档关系识别 | ≥90% |
| 高风险人工复核率 | 100% |
| 知识库来源可追溯 | 100% |
| 操作日志记录 | 100% |
| 严重数据安全事件 | 0 |

---

## 模块与提案章节映射

| 模块 | 提案章节 |
|------|---------|
| 企业端 Dashboard | §5.2 企业准入 |
| 单据上传与 OCR | §5.3-5.4, §6.2 数据采集与 OCR |
| 文档理解与交易图谱 | §5.5, §6.3-6.4 交易链构建、AI 文档理解 |
| 风险规则引擎 | §5.6-5.7, §6.6 完整性与风险评估、风险规则引擎 |
| 多币种现金流预测 | §5.8-5.10, §6.5 现金流分析、资金缺口、情景模拟 |
| 产品匹配与 RAG | §5.11, §6.7-6.8 金融产品匹配、RAG 知识库 |
| 预审报告 | §5.12 预审报告 |
| RM 工作台 | §5.13-5.14, §6.9 RM 协作与人工审核 |
| 监控与告警 | §5.15, §6.10-6.11 持续监控、AI 治理与数据安全 |
| 边界声明组件 | §6.10-6.11 AI 治理 |

---

## 说明

- `index.html`：原有概念展示页面，保留作为视觉参考
- `gba-bridge-finance.html`：`index.html` 的副本，内容完全相同
- 所有数据为演示假设（Illustrative assumptions），不构成实际金融建议
- 数据库为 SQLite，schema 设计兼容 PostgreSQL，可平滑迁移
- OCR 引擎支持 Tesseract（需安装），未安装时使用结构化数据模拟
