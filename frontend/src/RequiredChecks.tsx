import type { Workflow } from "./useBoletaWorkflow";

export function RequiredChecks({ w }: { w: Workflow }) {
  if (!w.result) return null;
  const selected = w.options.selected_records ?? w.result.records;
  const knownRows = new Set(
    w.result.records.map(
      (record) => `${record.source_sheet}:${record.source_row}`,
    ),
  );
  const knownSheets = new Set(
    w.result.records.map((record) => record.source_sheet),
  );
  const selectedSheets = new Set(selected.map((record) => record.source_sheet));
  const issues = w.result.issues.filter(
    (issue) =>
      issue.severity === "error" &&
      (!issue.type || selected.some((record) => record.type === issue.type)) &&
      (!knownSheets.has(issue.sheet ?? undefined) ||
        selectedSheets.has(issue.sheet ?? undefined)) &&
      (!knownRows.has(`${issue.sheet}:${issue.row}`) ||
        selected.some(
          (record) =>
            record.source_sheet === issue.sheet &&
            record.source_row === issue.row,
        )),
  );
  if (!issues.length) return null;
  return (
    <div className="required-checks">
      {issues.map((issue, index) => (
        <div
          className={
            issue.severity === "error" ? "field-error" : "required-check"
          }
          key={index}
          role={issue.severity === "error" ? "alert" : undefined}
        >
          {issue.code === "IVA_CONFIRMATION_REQUIRED" &&
          issue.sheet &&
          issue.row ? (
            <label className="check-label">
              <input
                type="checkbox"
                checked={w.options.zero_vat_confirmations.some(
                  (c) => c.sheet === issue.sheet && c.row === issue.row,
                )}
                onChange={(event) =>
                  w.changeOptions({
                    ...w.options,
                    zero_vat_confirmations: event.target.checked
                      ? [
                          ...w.options.zero_vat_confirmations,
                          { sheet: issue.sheet!, row: issue.row! },
                        ]
                      : w.options.zero_vat_confirmations.filter(
                          (c) => c.sheet !== issue.sheet || c.row !== issue.row,
                        ),
                  })
                }
              />
              Confirmo IVA vacío como cero · {issue.sheet}, fila {issue.row}.
            </label>
          ) : (
            <p>
              {issue.message}
              {issue.sheet && (
                <small>
                  {issue.sheet}
                  {issue.cell ? ` · ${issue.cell}` : ""}
                </small>
              )}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
