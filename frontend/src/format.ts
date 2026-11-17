export const currency = (value: string) =>
  new Intl.NumberFormat("es-SV", { style: "currency", currency: "USD" }).format(
    Number(value),
  );
