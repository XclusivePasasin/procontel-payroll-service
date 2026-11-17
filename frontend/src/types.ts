export type ExportFormat = "pdf" | "xlsx" | "both";
export type Kind = "planilla" | "honorarios";
export type Selection = Kind | "ambos";
export interface Identity {
  type: Kind;
  source_row: number;
  employee_id: string;
  source_sheet?: string;
}
export interface PaymentRecord extends Identity {
  sequence: number;
  fields: Record<string, string>;
  derived: Record<string, string>;
  final_net: string;
}
export interface Issue {
  code: string;
  severity: "error" | "warning" | "confirmation";
  type: Kind | null;
  sheet: string | null;
  cell: string | null;
  row: number | null;
  field: string | null;
  message: string;
}
export interface Period {
  start: string;
  end: string;
  confirmed: boolean;
}
export interface Options {
  selection: Selection;
  schema_version: string;
  file_sha256?: string;
  periods: Partial<Record<Kind, Period>>;
  zero_vat_confirmations: { sheet: string; row: number }[];
  selected_records: Identity[] | null;
  preview_record?: Identity;
  output_format?: ExportFormat;
}
export interface Analysis {
  can_generate: boolean;
  schema_version: string;
  file_sha256: string;
  company: string;
  records: PaymentRecord[];
  selected_count: number;
  issues: Issue[];
  source_issues: Issue[];
  types: Partial<
    Record<
      Kind,
      {
        count: number;
        selected_count: number;
        suggested_period: { start: string; end: string } | null;
        net_total: string;
        periods: { sheet: string; cell: string; value: string }[];
      }
    >
  >;
}
