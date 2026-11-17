import { useRef, useEffect } from "react";
import type { Workflow } from "./useBoletaWorkflow";
import type { PaymentRecord } from "./types";
import { identityOf, recordKey } from "./recordSelection";

function SelectionCheckbox({
  label,
  checked,
  partial,
  onChange,
}: {
  label: string;
  checked: boolean;
  partial: boolean;
  onChange: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (input.current) input.current.indeterminate = partial;
  }, [partial]);
  return (
    <input
      ref={input}
      type="checkbox"
      aria-label={label}
      checked={checked}
      onChange={onChange}
    />
  );
}

export function RecordsTable({ w }: { w: Workflow }) {
  const all = w.result?.records ?? [];
  const selected = new Set((w.options.selected_records ?? all).map(recordKey));
  const groups = new Map<string, PaymentRecord[]>();
  for (const record of all) {
    const area = record.fields.area?.trim() || "Sin área";
    groups.set(area, [...(groups.get(area) ?? []), record]);
  }
  function toggle(records: PaymentRecord[]) {
    const remove = records.every((r) => selected.has(recordKey(r)));
    const keys = new Set(selected);
    for (const record of records) {
      if (remove) keys.delete(recordKey(record));
      else keys.add(recordKey(record));
    }
    w.changeOptions({
      ...w.options,
      selected_records: all
        .filter((r) => keys.has(recordKey(r)))
        .map(identityOf),
    });
  }
  const count = all.filter((r) => selected.has(recordKey(r))).length;
  return (
    <section className="receipt-selection" aria-labelledby="selection-heading">
      <div className="selection-heading">
        <div>
          <h3 id="selection-heading">Seleccionar boletas</h3>
          <p aria-live="polite">
            {count} de {all.length} seleccionadas
          </p>
        </div>
      </div>
      <label className="selection-all">
        <SelectionCheckbox
          label="Seleccionar todas las boletas"
          checked={count === all.length && count > 0}
          partial={count > 0 && count < all.length}
          onChange={() => toggle(all)}
        />
        Seleccionar todas
      </label>
      {[...groups].map(([area, records]) => {
        const checked = records.filter((r) =>
          selected.has(recordKey(r)),
        ).length;
        return (
          <section
            className="area-group"
            key={area}
            aria-label={`Área ${area}`}
          >
            <header className="area-heading">
              <label>
                <SelectionCheckbox
                  label={`Seleccionar área ${area}`}
                  checked={checked === records.length}
                  partial={checked > 0 && checked < records.length}
                  onChange={() => toggle(records)}
                />
                <strong>{area}</strong>
              </label>
              <span>
                {checked} / {records.length}
              </span>
            </header>
            <ul>
              {records.map((record) => (
                <li className="person-row" key={recordKey(record)}>
                  <label>
                    <input
                      type="checkbox"
                      aria-label={`Seleccionar ${record.fields.name}${record.employee_id ? ` (${record.employee_id})` : ` (${record.source_sheet}, fila ${record.source_row})`}`}
                      checked={selected.has(recordKey(record))}
                      onChange={() => toggle([record])}
                    />
                    <span>
                      <strong>{record.fields.name}</strong>
                      <small>
                        {record.employee_id ? `${record.employee_id} · ` : ""}
                        {record.fields.role || "Sin cargo"}
                        {record.source_sheet &&
                        record.source_sheet !== record.type.toUpperCase()
                          ? ` · ${record.source_sheet}`
                          : ""}
                      </small>
                    </span>
                  </label>
                  <span className="person-type">
                    {record.type === "planilla" ? "Planilla" : "Honorarios"}
                  </span>
                  <button
                    className="text-button"
                    disabled={
                      !w.reviewed ||
                      !!w.busy ||
                      !selected.has(recordKey(record))
                    }
                    onClick={() => void w.run("preview", record)}
                  >
                    Ver PDF
                  </button>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
      {!all.length && (
        <p className="empty-state">No se encontraron personas.</p>
      )}
    </section>
  );
}
