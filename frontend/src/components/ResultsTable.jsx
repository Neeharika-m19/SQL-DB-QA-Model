import React from "react";

export default function ResultsTable({ data }) {
  if (!data || data.length === 0) {
    return <div className="text-sm text-gray-500">No rows.</div>;
  }

  const columns = Array.from(
    data.reduce((set, row) => {
      Object.keys(row || {}).forEach((k) => set.add(k));
      return set;
    }, new Set())
  );

  return (
    <div className="border rounded bg-white overflow-auto max-h-96">
      <table className="min-w-full text-sm">
        <thead className="sticky top-0 bg-gray-100">
          <tr>
            {columns.map((col) => (
              <th key={col} className="text-left px-3 py-2 font-semibold border-b">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rIdx) => (
            <tr key={rIdx} className={rIdx % 2 ? "bg-gray-50" : ""}>
              {columns.map((col) => (
                <td key={col} className="px-3 py-2 border-b align-top">
                  {formatCell(row?.[col])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatCell(v) {
  if (v === null || v === undefined) return <span className="text-gray-400">—</span>;
  if (typeof v === "object") return <code className="text-xs">{JSON.stringify(v)}</code>;
  return String(v);
}
