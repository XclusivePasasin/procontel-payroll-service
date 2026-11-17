import { PeriodConfirmation } from "./PeriodConfirmation";
import { RequiredChecks } from "./RequiredChecks";
import { RecordsTable } from "./RecordsTable";
import { useRef } from "react";
import {
  ArrowRight,
  Check,
  Download,
  FileCheck2,
  FileSpreadsheet,
  LoaderCircle,
  LockKeyhole,
  Upload,
  X,
} from "lucide-react";
import { useBoletaWorkflow } from "./useBoletaWorkflow";
import type { Kind, Selection } from "./types";
import { recordKey } from "./recordSelection";
export default function App() {
  const w = useBoletaWorkflow();
  const input = useRef<HTMLInputElement>(null);
  const kinds: Kind[] =
    w.options.selection === "ambos"
      ? ["planilla", "honorarios"]
      : [w.options.selection];
  const selectedRecords =
    w.result?.records.filter((r) =>
      w.options.selected_records?.some((s) => recordKey(s) === recordKey(r)),
    ) ?? [];
  const selectedKinds: Kind[] = kinds.filter((kind) =>
    selectedRecords.some((r) => r.type === kind),
  );
  const downloadLabel =
    selectedRecords.length === 1
      ? "Descargar boleta PDF"
      : new Set(
            selectedRecords.map((record) => record.source_sheet ?? record.type),
          ).size > 1
        ? "Descargar PDFs en ZIP"
        : "Descargar boletas PDF";
  const downloadsLocked = !w.reviewed || !!w.busy || !selectedRecords.length;
  function setFile(file: File | null) {
    if (input.current) input.current.value = "";
    w.selectFile(file);
  }
  return (
    <div className="app-shell">
      <div className="main-shell">
        <main id="main">
          <div className="page-heading">
            <div>
              <h1>Boletas de pago</h1>
              <p>Carga tu Excel para revisar y generar boletas.</p>
            </div>
          </div>
          <ol className="steps" aria-label="Etapas del proceso">
            {[
              "Carga tu archivo",
              "Revisa y confirma",
              "Descarga las boletas",
            ].map((label, i) => (
              <li
                className={
                  (w.reviewed ? 2 : w.result ? 1 : 0) >= i ? "current" : ""
                }
                key={label}
              >
                <span>
                  {w.result && i === 0 ? (
                    <Check size={15} />
                  ) : (
                    String(i + 1).padStart(2, "0")
                  )}
                </span>
                {label}
              </li>
            ))}
          </ol>
          <div className="workflow-grid">
            <section className="card upload-card">
              <div className="card-heading">
                <div>
                  <h2>Archivo de planilla</h2>
                </div>
              </div>
              <input
                ref={input}
                type="file"
                className="sr-only"
                id="file"
                aria-label="Archivo Excel .xlsx"
                accept=".xlsx"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
              <button
                className={`drop-zone ${w.file ? "has-file" : ""}`}
                onClick={() => input.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  setFile(e.dataTransfer.files[0] ?? null);
                }}
                aria-label="Seleccionar archivo Excel"
              >
                <span className="upload-icon">
                  {w.file ? (
                    <FileSpreadsheet size={27} />
                  ) : (
                    <Upload size={25} />
                  )}
                </span>
                <strong>
                  {w.file ? w.file.name : "Arrastra tu archivo Excel aquí"}
                </strong>
                <span>
                  {w.file
                    ? `${(w.file.size / 1024).toFixed(1)} KB · Cambiar archivo`
                    : "o haz clic para seleccionarlo"}
                </span>
                <small>.XLSX · Máximo 10 MB · Sin macros</small>
              </button>
              <fieldset className="output-selector">
                <legend>¿Qué boletas necesitas?</legend>
                {(["planilla", "honorarios", "ambos"] as Selection[]).map(
                  (value, i) => (
                    <label
                      className={
                        w.options.selection === value ? "selected" : ""
                      }
                      key={value}
                    >
                      <input
                        type="radio"
                        name="output"
                        checked={w.options.selection === value}
                        onChange={() => {
                          w.selectOutput(value);
                        }}
                      />
                      <span>
                        {["Planilla", "Honorarios", "Ambos tipos"][i]}
                      </span>
                      {value === "ambos" && <small>ZIP</small>}
                    </label>
                  ),
                )}
              </fieldset>
              <div className="card-action">
                <span>
                  <LockKeyhole size={14} />
                  Procesamiento en memoria · Sin almacenamiento
                </span>
                <button
                  className="primary"
                  disabled={!w.file || !!w.busy || w.file.size > 10485760}
                  onClick={() => void w.run("analyze")}
                >
                  {w.busy === "analyze" ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : null}
                  Analizar archivo
                  <ArrowRight size={16} />
                </button>
              </div>
            </section>
          </div>
          {w.error && (
            <div role="alert" className="error-banner">
              {w.error}
            </div>
          )}
          {w.busy && (
            <div role="status" className="busy-bar">
              <LoaderCircle className="spin" size={18} />
              Procesando {w.busy === "analyze" ? "el archivo" : "la solicitud"}…
              <button onClick={w.cancel}>Cancelar</button>
            </div>
          )}
          {w.result && (
            <section className="card review-section">
              <div className="card-heading">
                <div>
                  <h2>Revisión antes de emitir</h2>
                </div>
                <button
                  className="text-button ml-auto"
                  onClick={() => {
                    setFile(null);
                    w.clear();
                  }}
                >
                  <X size={15} />
                  Limpiar
                </button>
              </div>
              <p className="company-name">{w.result.company}</p>
              <RecordsTable w={w} />
              <PeriodConfirmation w={w} kinds={selectedKinds} />
              <RequiredChecks w={w} />
              <div className="download-bar">
                <p aria-live="polite">
                  {w.reviewed
                    ? "Revisión validada. Puedes descargar las boletas."
                    : "1. Revisa las boletas para habilitar las descargas."}
                </p>
                <button
                  className="secondary action-review"
                  disabled={!!w.busy || !selectedRecords.length}
                  onClick={() => void w.run("review")}
                >
                  {w.busy === "review" ? (
                    <LoaderCircle className="spin" size={17} />
                  ) : w.reviewed ? (
                    <Check size={17} />
                  ) : (
                    <FileCheck2 size={17} />
                  )}
                  {w.busy === "review"
                    ? "Revisando…"
                    : w.reviewed
                      ? "Revisar de nuevo"
                      : "Revisar boletas"}
                </button>
                <button
                  className="secondary action-pdf"
                  disabled={downloadsLocked}
                  title={
                    w.reviewed
                      ? "Descargar las boletas seleccionadas en PDF"
                      : "Primero revisa las boletas"
                  }
                  onClick={() => void w.run("generate")}
                >
                  <Download size={17} />
                  {downloadLabel}
                </button>
                <button
                  className="secondary action-excel"
                  disabled={downloadsLocked}
                  title={
                    w.reviewed
                      ? "Descargar el Excel original con sus hojas de boletas"
                      : "Primero revisa las boletas"
                  }
                  onClick={() => void w.run("generate", undefined, "xlsx")}
                >
                  <FileSpreadsheet size={16} />
                  Descargar Excel
                </button>
                <button
                  className="secondary action-bundle"
                  disabled={downloadsLocked}
                  title={
                    w.reviewed
                      ? "Descargar un ZIP con el Excel y todas las boletas PDF"
                      : "Primero revisa las boletas"
                  }
                  onClick={() => void w.run("generate", undefined, "both")}
                >
                  <Download size={16} />
                  Descargar todo (ZIP)
                </button>
              </div>
              {w.preview && (
                <section className="preview">
                  <h3>Vista previa</h3>
                  <iframe title="Vista previa de la boleta" src={w.preview} />
                  <a href={w.preview} target="_blank" rel="noreferrer">
                    Abrir vista previa en otra pestaña
                  </a>
                </section>
              )}
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
