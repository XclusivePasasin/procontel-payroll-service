import { useId, useState } from "react";
import { CalendarIcon } from "lucide-react";
import { format, isValid, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { Button } from "./button";
import { Calendar } from "./calendar";
import { Popover, PopoverContent, PopoverTrigger } from "./popover";

interface DatePickerProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  invalid?: boolean;
}

export function DatePicker({
  label,
  value,
  onChange,
  invalid,
}: DatePickerProps) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const parsed = value ? parseISO(value) : undefined;
  const date = parsed && isValid(parsed) ? parsed : undefined;
  return (
    <div className="date-picker-field">
      <label htmlFor={id}>{label}</label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            id={id}
            type="button"
            variant="outline"
            aria-label={label}
            aria-invalid={invalid || undefined}
            className="date-trigger"
          >
            <span>
              {date ? format(date, "dd/MM/yyyy") : "Seleccionar fecha"}
            </span>
            <CalendarIcon size={16} />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          className="date-popover"
          align="start"
          collisionPadding={12}
        >
          <Calendar
            mode="single"
            required
            locale={es}
            formatters={{
              formatMonthDropdown: (month) =>
                format(month, "MMM", { locale: es }),
            }}
            selected={date}
            defaultMonth={date}
            captionLayout="dropdown"
            startMonth={new Date(2000, 0)}
            endMonth={new Date(2100, 11)}
            onSelect={(selected) => {
              if (selected) {
                onChange(format(selected, "yyyy-MM-dd"));
                setOpen(false);
              }
            }}
            autoFocus
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}
