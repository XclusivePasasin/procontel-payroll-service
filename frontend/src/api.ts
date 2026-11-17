import type { Analysis, Options } from "./types";
export async function request(
  action: string,
  file: File,
  options: Options,
  signal: AbortSignal,
): Promise<Response> {
  const form = new FormData();
  form.append("file", file);
  form.append("options", JSON.stringify(options));
  const response = await fetch(`/api/v1/${action}`, {
    method: "POST",
    body: form,
    signal,
    cache: "no-store",
  });
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as {
      message?: string;
      request_id?: string;
    } | null;
    throw new Error(
      error?.message ??
        `No se pudo completar la solicitud (${response.status}).`,
    );
  }
  return response;
}
export async function analyze(
  action: string,
  file: File,
  options: Options,
  signal: AbortSignal,
): Promise<Analysis> {
  return (
    await request(action, file, options, signal)
  ).json() as Promise<Analysis>;
}
