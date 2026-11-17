import { identityOf } from "./recordSelection";
import { useEffect, useRef, useState } from "react";
import { analyze, request } from "./api";
import type {
  Analysis,
  ExportFormat,
  Identity,
  Options,
  Selection,
} from "./types";
const initial = (selection: Selection = "ambos"): Options => ({
  selection,
  schema_version: "procontel_fixed_v1",
  periods: {},
  zero_vat_confirmations: [],
  selected_records: null,
});
export function useBoletaWorkflow() {
  const [file, setFile] = useState<File | null>(null);
  const [options, setOptions] = useState<Options>(initial);
  const [result, setResult] = useState<Analysis | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState("");
  const controller = useRef<AbortController | null>(null);
  const previewRef = useRef("");
  const revision = useRef(0);
  function revoke() {
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = "";
    setPreview("");
  }
  function invalidate() {
    revision.current++;
    controller.current?.abort();
    setBusy("");
    setReviewed(false);
    revoke();
    setError("");
  }
  function changeOptions(value: Options) {
    invalidate();
    setOptions(value);
  }
  function selectFile(value: File | null) {
    invalidate();
    setFile(value);
    setResult(null);
    setOptions(initial(options.selection));
  }
  function selectOutput(value: Selection) {
    invalidate();
    setResult(null);
    setOptions(initial(value));
  }
  function clear() {
    selectFile(null);
  }
  function cancel() {
    invalidate();
  }
  useEffect(
    () => () => {
      controller.current?.abort();
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    },
    [],
  );
  async function run(
    action: "analyze" | "review" | "preview" | "generate",
    identity?: Identity,
    outputFormat: ExportFormat = "pdf",
  ) {
    if (!file) return;
    if ((action === "preview" || action === "generate") && !reviewed) return;
    if (action === "review" || action === "analyze") setReviewed(false);
    const current = revision.current;
    const abort = new AbortController();
    controller.current?.abort();
    controller.current = abort;
    setBusy(action);
    setError("");
    const requestOptions = { ...options, periods: { ...options.periods } };
    if (action === "review") {
      for (const kind of ["planilla", "honorarios"] as const) {
        const period = requestOptions.periods[kind];
        if (period)
          requestOptions.periods[kind] = {
            ...period,
            confirmed:
              !!period.start && !!period.end && period.start <= period.end,
          };
      }
    }
    try {
      if (action === "analyze" || action === "review") {
        const response = await analyze(
          action,
          file,
          action === "analyze"
            ? { ...options, selected_records: null }
            : requestOptions,
          abort.signal,
        );
        if (current !== revision.current) return;
        setResult(response);
        setOptions((old) => {
          const periods = { ...requestOptions.periods };
          if (action === "analyze") {
            const suggestion =
              response.types.planilla?.suggested_period ??
              response.types.honorarios?.suggested_period;
            const shared = {
              start: suggestion?.start ?? "",
              end: suggestion?.end ?? "",
              confirmed: false,
            };
            periods.planilla = { ...shared };
            periods.honorarios = { ...shared };
          }
          return {
            ...old,
            file_sha256: response.file_sha256,
            periods,
            selected_records:
              action === "analyze"
                ? response.records.map(identityOf)
                : old.selected_records,
          };
        });
        setReviewed(action === "review" && response.can_generate);
      } else {
        const response = await request(
          action,
          file,
          {
            ...options,
            output_format: outputFormat,
            preview_record: identity
              ? {
                  type: identity.type,
                  source_row: identity.source_row,
                  employee_id: identity.employee_id,
                  source_sheet: identity.source_sheet,
                }
              : undefined,
          },
          abort.signal,
        );
        const blob = await response.blob();
        if (current !== revision.current) return;
        const url = URL.createObjectURL(blob);
        if (action === "preview") {
          revoke();
          previewRef.current = url;
          setPreview(url);
        } else {
          const link = document.createElement("a");
          link.href = url;
          link.download =
            response.headers
              .get("content-disposition")
              ?.match(/filename="([^"]+)"/)?.[1] ?? "boletas.pdf";
          link.click();
          setTimeout(() => URL.revokeObjectURL(url), 1000);
        }
      }
    } catch (err) {
      if (
        current === revision.current &&
        !(err instanceof DOMException && err.name === "AbortError")
      )
        setError(err instanceof Error ? err.message : "Error inesperado.");
    } finally {
      if (current === revision.current) setBusy("");
    }
  }
  return {
    file,
    options,
    result,
    reviewed,
    busy,
    error,
    preview,
    changeOptions,
    selectFile,
    selectOutput,
    clear,
    cancel,
    run,
  };
}

export type Workflow = ReturnType<typeof useBoletaWorkflow>;
