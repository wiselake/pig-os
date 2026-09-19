"use client";

import { Download, Printer } from "lucide-react";

// 리포트 공용 내보내기 바 — CSV(콜백) + PDF(브라우저 인쇄→PDF, 외부 라이브러리 없음).
// PDF는 globals.css의 @media print + 리포트 컨텐츠의 .print-area 로 동작.
export function ReportExportBar({
  onCsv,
  csvDisabled,
}: {
  onCsv?: () => void;
  csvDisabled?: boolean;
}) {
  return (
    <div className="no-print flex items-center gap-2">
      {onCsv && (
        <button
          onClick={onCsv}
          disabled={csvDisabled}
          className="inline-flex items-center gap-1.5 text-sm font-semibold border border-border rounded-xl px-3.5 py-2 hover:border-primary disabled:opacity-50"
        >
          <Download size={16} /> CSV
        </button>
      )}
      <button
        onClick={() => window.print()}
        className="inline-flex items-center gap-1.5 text-sm font-semibold border border-border rounded-xl px-3.5 py-2 hover:border-primary"
      >
        <Printer size={16} /> PDF
      </button>
    </div>
  );
}
