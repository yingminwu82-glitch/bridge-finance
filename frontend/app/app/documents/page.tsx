"use client";

import { useState, useEffect, useCallback } from "react";
import {
  apiGet, apiPost, apiPostForm, formatCurrency, DocumentItem, Transaction,
} from "@/lib/api";

export default function DocumentsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedTx, setSelectedTx] = useState<number>(1);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentItem | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");

  const loadDocs = useCallback((txId: number) => {
    apiGet(`/api/documents?transaction_id=${txId}`).then((data) => {
      setDocuments(data.documents || []);
      setLoading(false);
    });
  }, []);

  useEffect(() => {
    apiGet("/api/transactions").then((data) => {
      setTransactions(data.transactions || []);
      if (data.transactions?.length > 0) {
        const txId = data.transactions[0].id;
        setSelectedTx(txId);
        loadDocs(txId);
      }
    });
  }, [loadDocs]);

  const handleTxChange = (txId: number) => {
    setSelectedTx(txId);
    setSelectedDoc(null);
    setMessage("");
    loadDocs(txId);
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setMessage("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("enterprise_id", "1");
      const result = await apiPostForm(
        `/api/documents/upload?enterprise_id=1&transaction_id=${selectedTx}`,
        formData
      );
      setMessage(`✓ ${file.name} 已上传，识别为 ${result.doc_type}`);
      loadDocs(selectedTx);
    } catch (err: any) {
      setMessage(`✗ 上传失败: ${err.message}`);
    }
    setUploading(false);
    e.target.value = "";
  };

  const handleReprocess = async (docId: number) => {
    setMessage("");
    try {
      const result = await apiPost(`/api/documents/${docId}/ocr`);
      setMessage(`✓ OCR 重新处理完成: ${result.doc_type}`);
      loadDocs(selectedTx);
      if (selectedDoc?.id === docId) {
        setSelectedDoc(result);
      }
    } catch (err: any) {
      setMessage(`✗ OCR 处理失败: ${err.message}`);
    }
  };

  const handleConfirm = async (docId: number) => {
    setMessage("");
    try {
      await apiPost(`/api/documents/${docId}/confirm?reviewer=rm`);
      setMessage("✓ OCR 字段已确认");
      loadDocs(selectedTx);
    } catch (err: any) {
      setMessage(`✗ 确认失败: ${err.message}`);
    }
  };

  const currentTx = transactions.find((t) => t.id === selectedTx);
  const allConfirmed = documents.length > 0 && documents.every((d) => d.confirmed);

  return (
    <div className="fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">单据上传与 OCR 识别</h1>
        <p className="text-sm text-[#6b6b73]">
          上传交易单据，AI 自动识别文档类型并提取关键字段
        </p>
      </div>

      {/* Transaction selector */}
      <div className="flex gap-2 mb-4 flex-wrap items-center">
        <span className="text-sm font-medium text-[#6b6b73]">选择交易：</span>
        {transactions.map((tx) => (
          <button
            key={tx.id}
            onClick={() => handleTxChange(tx.id)}
            className={`px-3 py-1.5 rounded-lg text-sm border transition ${
              selectedTx === tx.id
                ? "bg-[#a91624] text-white border-[#a91624]"
                : "bg-white border-[#e5e5e8] hover:border-[#a91624]"
            }`}
          >
            {tx.tx_ref}
          </button>
        ))}
      </div>

      {currentTx && (
        <div className="card mb-4 text-sm">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div><span className="text-[#9b9ba3]">买家：</span>{currentTx.buyer}</div>
            <div><span className="text-[#9b9ba3]">供应商：</span>{currentTx.supplier}</div>
            <div><span className="text-[#9b9ba3]">订单：</span>{formatCurrency(currentTx.order_amount, currentTx.order_currency)}</div>
            <div><span className="text-[#9b9ba3]">发票：</span>{formatCurrency(currentTx.invoice_amount, currentTx.invoice_currency)}</div>
          </div>
        </div>
      )}

      {/* Upload area */}
      <div className="card mb-4">
        <label className="block">
          <div className="border-2 border-dashed border-[#e5e5e8] rounded-xl p-8 text-center hover:border-[#a91624] transition cursor-pointer">
            <div className="text-3xl mb-2">📎</div>
            <div className="font-medium mb-1">上传单据</div>
            <div className="text-xs text-[#9b9ba3]">
              支持 PDF / 图片 / Excel · 订单、合同、发票、物流单、付款通知
            </div>
          </div>
          <input
            type="file"
            className="hidden"
            onChange={handleUpload}
            accept=".pdf,.png,.jpg,.jpeg,.xlsx,.xls"
            disabled={uploading}
          />
        </label>
        {uploading && <div className="text-center mt-2 text-sm text-[#a91624]">上传处理中...</div>}
      </div>

      {message && (
        <div className="mb-4 p-3 rounded-lg text-sm" style={{
          background: message.startsWith("✓") ? "#dcfce7" : "#fee2e2",
          color: message.startsWith("✓") ? "#166534" : "#991b1b",
        }}>
          {message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Document list */}
        <div className="lg:col-span-1">
          <h2 className="font-bold mb-3">已上传单据 ({documents.length})</h2>
          <div className="space-y-2">
            {documents.map((doc) => (
              <div
                key={doc.id}
                onClick={() => setSelectedDoc(doc)}
                className={`card cursor-pointer transition ${
                  selectedDoc?.id === doc.id ? "ring-2 ring-[#a91624]" : ""
                }`}
                style={{ padding: "12px" }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{doc.filename}</div>
                    <div className="text-xs text-[#9b9ba3] mt-1">{doc.doc_type}</div>
                  </div>
                  {doc.confirmed ? (
                    <span className="text-xs px-2 py-0.5 rounded bg-[#dcfce7] text-[#166534] shrink-0">已确认</span>
                  ) : doc.low_confidence_fields.length > 0 ? (
                    <span className="text-xs px-2 py-0.5 rounded bg-[#fef3c7] text-[#92400e] shrink-0">待确认</span>
                  ) : (
                    <span className="text-xs px-2 py-0.5 rounded bg-[#f7f7f8] text-[#6b6b73] shrink-0">已识别</span>
                  )}
                </div>
                <div className="text-xs text-[#9b9ba3] mt-1">
                  类型置信度: {(doc.doc_type_confidence * 100).toFixed(0)}%
                </div>
              </div>
            ))}
            {documents.length === 0 && !loading && (
              <div className="text-center text-sm text-[#9b9ba3] py-8">暂无单据</div>
            )}
          </div>
        </div>

        {/* Document detail / OCR fields */}
        <div className="lg:col-span-2">
          {selectedDoc ? (
            <div className="card">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="font-bold">{selectedDoc.filename}</h2>
                  <div className="text-sm text-[#6b6b73] mt-1">
                    文档类型：{selectedDoc.doc_type}（置信度 {(selectedDoc.doc_type_confidence * 100).toFixed(0)}%）
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleReprocess(selectedDoc.id)}
                    className="btn-secondary btn-sm"
                  >
                    重新 OCR
                  </button>
                  <button
                    onClick={() => handleConfirm(selectedDoc.id)}
                    className="btn-primary btn-sm"
                    disabled={selectedDoc.confirmed}
                  >
                    {selectedDoc.confirmed ? "已确认 ✓" : "确认字段"}
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                {Object.entries(selectedDoc.structured_data || {}).map(([field, value]) => {
                  const conf = selectedDoc.ocr_confidence?.[field] ?? 0.95;
                  const lowConf = conf < 0.85;
                  return (
                    <div key={field} className="flex items-center justify-between p-3 rounded-lg border border-[#e5e5e8]">
                      <div className="flex-1">
                        <div className="text-xs text-[#9b9ba3] mb-0.5">{field}</div>
                        <div className="font-medium text-sm">{value}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-[#f7f7f8] rounded-full h-2 overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${conf * 100}%`,
                              background: lowConf ? "#f59e0b" : "#16a34a",
                            }}
                          />
                        </div>
                        <span
                          className={`text-xs px-2 py-0.5 rounded ${
                            lowConf ? "risk-medium" : "risk-low"
                          }`}
                        >
                          {(conf * 100).toFixed(0)}%
                        </span>
                        {lowConf && (
                          <span className="text-xs text-[#f59e0b] font-medium whitespace-nowrap">
                            Low Confidence
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {selectedDoc.low_confidence_fields.length > 0 && !selectedDoc.confirmed && (
                <div className="mt-4 p-3 rounded-lg bg-[#fef3c7] border border-[#f0d060] text-sm text-[#92400e]">
                  ⚠ 以下字段置信度低于 85%，需 RM 人工确认后方可进入后续分析：
                  <span className="font-medium ml-1">{selectedDoc.low_confidence_fields.join(", ")}</span>
                </div>
              )}

              {selectedDoc.confirmed && (
                <div className="mt-4 p-3 rounded-lg bg-[#dcfce7] border border-[#86efac] text-sm text-[#166534]">
                  ✓ 字段已由 RM 确认，可进入后续分析流程
                </div>
              )}
            </div>
          ) : (
            <div className="card text-center py-16 text-[#9b9ba3]">
              选择左侧单据查看 OCR 识别结果
            </div>
          )}

          {/* Pipeline status */}
          {documents.length > 0 && (
            <div className="card mt-4">
              <h3 className="font-bold text-sm mb-3">分析流程状态</h3>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`px-3 py-1 rounded text-xs font-medium ${allConfirmed ? "bg-[#dcfce7] text-[#166534]" : "bg-[#fef3c7] text-[#92400e]"}`}>
                  1. OCR 识别 {documents.length > 0 ? "✓" : "○"}
                </span>
                <span className="text-[#9b9ba3]">→</span>
                <span className={`px-3 py-1 rounded text-xs font-medium ${allConfirmed ? "bg-[#dcfce7] text-[#166534]" : "bg-[#f7f7f8] text-[#6b6b73]"}`}>
                  2. RM 确认 {allConfirmed ? "✓" : "○"}
                </span>
                <span className="text-[#9b9ba3]">→</span>
                <span className="px-3 py-1 rounded text-xs font-medium bg-[#f7f7f8] text-[#6b6b73]">
                  3. 文档理解
                </span>
                <span className="text-[#9b9ba3]">→</span>
                <span className="px-3 py-1 rounded text-xs font-medium bg-[#f7f7f8] text-[#6b6b73]">
                  4. 风险评估
                </span>
                <span className="text-[#9b9ba3]">→</span>
                <span className="px-3 py-1 rounded text-xs font-medium bg-[#f7f7f8] text-[#6b6b73]">
                  5. 产品匹配
                </span>
              </div>
              <div className="mt-3 flex gap-2">
                <a href={`/app/graph?tx=${selectedTx}`} className="btn-primary btn-sm">查看交易图谱 →</a>
                <a href={`/app/cashflow?tx=${selectedTx}`} className="btn-secondary btn-sm">现金流分析 →</a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
