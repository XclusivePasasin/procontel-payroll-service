import type { Identity } from "./types";
export const recordKey = (record: Identity) =>
  `${record.type}:${record.source_sheet ?? record.type.toUpperCase()}:${record.source_row}:${record.employee_id}`;
export const identityOf = ({
  type,
  source_row,
  employee_id,
  source_sheet,
}: Identity): Identity => ({ type, source_row, employee_id, source_sheet });
