# 演示脚本

## 前提条件

- 后端运行在 http://localhost:8000
- 前端运行在 http://localhost:3000

## 演示流程（约 15 分钟）

### 1. 概念首页（1 分钟）

- 打开 http://localhost:3000
- 展示概念首页：跨境贸易金融智能分析平台
- 介绍四大能力：交易信息结构化、资金需求早识别、多币种视角、全流程服务连接
- 点击"进入应用"

### 2. 企业端首页（1 分钟）

- 路由：`/app/dashboard`
- 切换企业：利丰贸易（香港） vs 深圳科创
- 展示企业信息卡片（区域、行业、币种、经营模式）
- 展示交易列表：TX-A-001（USD 500K）和 TX-B-001（USD 5M）
- 每个交易显示：买家、供应商、金额、完整度、风险等级

### 3. 单据上传与 OCR（3 分钟）

- 路由：`/app/documents`
- 选择 TX-A-001
- 展示已上传的 4 个单据：
  1. PO_ABC_2026.pdf → Purchase Order（置信度 98%）
  2. SalesContract_001.pdf → Sales Contract（置信度 97%）
  3. SupplierInvoice_INV20260815.pdf → Commercial Invoice（置信度 96%）
  4. PaymentSchedule.xlsx → Payment Schedule（置信度 99%）
- 点击单据查看 OCR 字段：
  - 每个字段显示值和置信度条
  - 低置信度字段（<85%）标黄，显示"Low Confidence – Please Verify"
  - Payment Due Date 置信度 82% → 需 RM 确认
  - Account 置信度 82% → 需 RM 确认
- 点击"确认字段"模拟 RM 确认
- 展示分析流程状态条：OCR → RM 确认 → 文档理解 → 风险评估 → 产品匹配
- （可选）上传新文件测试 OCR

### 4. 交易关系图谱（2 分钟）

- 路由：`/app/graph`
- 选择 TX-A-001
- 展示图谱可视化：
  - 中心：企业节点（红色）
  - 周围：客户（蓝色）、供应商（绿色）、银行账户（橙色）、物流（紫色）
  - 外圈：单据节点（灰色）
  - 连线显示关系类型（sells_to, purchases_from, owns_account 等）
- 点击节点查看详情
- 右侧面板展示：
  - 交易完整度评分（88/100）
  - 风险维度（5 个维度 + Overall）
  - 单据确认状态

### 5. 现金流与情景模拟（4 分钟）

- 路由：`/app/cashflow`
- 选择 TX-A-001

#### 5.1 现金流时间线
- ECharts 柱状图展示：
  - 绿色：inflow（客户收款 USD 500K）
  - 红色：outflow（供应商付款 CNY 3.6M、运营费用 HKD）

#### 5.2 资金缺口分析
- Funding Gap：CNY 3,600,000，持续 66 天
- 开始日期：2026-10-15（供应商付款日）
- 结束日期：2026-12-20（客户收款日）
- 主要原因：CNY 供应商付款先于 USD 客户收款，存在时间错配和币种错配

#### 5.3 情景模拟
- 5 个情景对比柱状图：
  1. Base Case: CNY 3.6M
  2. Customer Delay +15d: CNY 3.6M（缺口延长）
  3. CNY Appreciation +3%: CNY 3.71M（成本增加）
  4. Supplier Early Payment: CNY 3.6M（缺口提前）
  5. Combined Stress: CNY 4.5M（综合压力最大）

#### 5.4 风险规则引擎
- 点击"运行风险分析"
- 展示结果：
  - 完整度：88/100
  - 整体风险：Medium
  - 需人工复核：是（高风险）
  - 5 个风险维度表格
  - 风险告警列表（每条可展开 Why）：
    - FX Exposure: High（CNY/USD 错配）
    - Payment Account Change: Medium（新账户）
    - Missing Information: Medium（缺物流单）

### 6. 预审报告（2 分钟）

- 路由：`/app/report`
- 选择 TX-A-001
- 点击"生成报告"
- 展示报告内容：
  - 报告编号、生成时间
  - AI 分析摘要
  - 企业信息
  - 交易信息
  - 风险分析（完整度、维度、告警）
  - 资金需求分析（缺口、情景摘要）
  - 金融服务推荐（4 条推荐，含 Source/Knowledge Reference）
  - RM 审核要求提示

### 7. RM 工作台（3 分钟）

- 路由：`/rm/dashboard`
- 展示仪表盘统计（总交易数、高风险、待审核、推荐数）
- 选择 TX-A-001 查看详情：
  - AI 分析摘要
  - 交易概览（金额、缺口、物流）
  - 风险维度
  - 风险告警（可展开 Why）
  - 产品推荐（含 Source 可展开）
- 执行 RM 操作：
  - 选择"添加风险评论"
  - 输入评论
  - 点击"执行操作"
  - 查看操作确认消息
- 展示审计日志（底部表格）

### 8. 监控与告警（1 分钟）

- 路由：`/monitoring`
- 展示监控事件时间线：
  - 物流更新（info）
  - 汇率变动（warning）
  - 收款状态（info）
- 按严重程度筛选
- 每个事件可展开查看详细元数据

---

## 关键演示要点

1. **OCR 置信度机制**：低置信度字段（<85%）自动标黄，阻断后续分析，需 RM 确认
2. **交易关系图谱**：可视化展示订单→合同→发票→物流→付款→应收的完整链路
3. **多币种现金流**：CNY/USD/HKD 三币种，Future Cash Position 计算
4. **资金缺口**：自动识别时间错配和币种错配导致的缺口
5. **5 个情景模拟**：从基准到综合压力测试
6. **风险规则引擎**：5 类风险维度，每条告警含 What/Why/What-next
7. **RAG 可追溯**：每条产品推荐含 Source/Knowledge Reference
8. **边界声明**：贯穿所有页面，AI 辅助不构成信贷审批
9. **高风险 100% 人工复核**：Flag → Escalate → RM Review
10. **审计日志**：所有操作记录可查

---

## 切换到案例 B 演示

重复上述步骤，选择 TX-B-001：
- USD 5M 订单，CNY 30M 供应商付款
- Peak Funding Gap: CNY 30,000,000
- 展示更大规模的 FX Exposure 和资金缺口
