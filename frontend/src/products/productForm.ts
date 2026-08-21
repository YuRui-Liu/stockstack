import type { ErrorResponse, ProductImageInput } from "../api/types";

export function fieldErrorsToForm(fieldErrors: ErrorResponse["field_errors"]) {
  return Object.entries(fieldErrors).map(([path, errors]) => ({ name: path.split("."), errors }));
}

export function imageInputs(images: Array<ProductImageInput & { sort_order?: number }>): ProductImageInput[] {
  return images.map(({ kind, url, size_bytes, mime_type }) => ({ kind, url, size_bytes, mime_type }));
}

export function normalizeAttributes(attributes: Record<string, unknown> = {}) {
  return Object.fromEntries(Object.entries(attributes).map(([key, value]) => [key, value && typeof value === "object" && "format" in value && typeof (value as { format: unknown }).format === "function" ? (value as { format: (format: string) => string }).format("YYYY-MM-DD") : value]));
}
