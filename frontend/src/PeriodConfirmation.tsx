import type { Workflow } from "./useBoletaWorkflow";
import type { Kind, Period } from "./types";
import { DatePicker } from "./components/ui/date-picker";

export function PeriodConfirmation({
  w,
  kinds,
}: {
  w: Workflow;
  kinds: Kind[];
}) {
  if (!kinds.length) return null;
  const period: Period = w.options.periods.planilla ??
    w.options.periods.honorarios ?? { start: "", end: "", confirmed: false };
  const invalid = !!period.start && !!period.end && period.start > period.end;
  function update(value: Period) {
    w.changeOptions({
      ...w.options,
      periods: { planilla: { ...value }, honorarios: { ...value } },
    });
  }
  return (
    <div className="period-grid">
      <fieldset>
        <legend>Período de pago</legend>
        <div className="date-fields">
          <DatePicker
            label="Desde"
            value={period.start}
            onChange={(value) =>
              update({ ...period, start: value, confirmed: false })
            }
            invalid={invalid}
          />
          <DatePicker
            label="Hasta"
            value={period.end}
            onChange={(value) =>
              update({ ...period, end: value, confirmed: false })
            }
            invalid={invalid}
          />
        </div>
        {invalid && (
          <p className="field-error" role="alert">
            La fecha final debe ser igual o posterior a la inicial.
          </p>
        )}
      </fieldset>
    </div>
  );
}
