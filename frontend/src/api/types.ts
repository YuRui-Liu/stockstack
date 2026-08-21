export interface ErrorResponse {
  code: string;
  message: string;
  field_errors: Record<string, string[]>;
  request_id: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export type ProductType = "physical" | "virtual" | "creative";
export type ProductStatus = "on_shelf" | "off_shelf" | "penalized";
export type DeliveryMethod = "ems" | "logistics" | "voucher";
export type ReturnRule = "seven_days" | "no_returns";
export type ImageMimeType = "image/jpeg" | "image/png" | "image/webp";

export interface JSONSchemaProperty {
  type?: string;
  title?: string;
  description?: string;
  enum?: ReadonlyArray<string | number>;
  format?: string;
  minimum?: number;
  maximum?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  [key: string]: unknown;
}

export interface FieldSchemaDocument {
  $schema?: string;
  type: "object";
  properties: Record<string, JSONSchemaProperty>;
  required?: readonly string[];
  additionalProperties?: boolean;
  [key: string]: unknown;
}

export interface FieldSchema {
  product_type: ProductType;
  version: number;
  schema: FieldSchemaDocument;
}

export interface ProductImageInput {
  kind: "main" | "gallery";
  url: string;
  size_bytes: number;
  mime_type: ImageMimeType;
}

export interface ProductImageView extends ProductImageInput { sort_order: number }

export interface ProductCreate {
  title: string;
  short_title: string;
  description_html: string;
  price_amount: string;
  stock: number;
  product_type: ProductType;
  status: ProductStatus;
  delivery_method: DeliveryMethod;
  return_rule: ReturnRule;
  attributes: Record<string, unknown>;
  schema_version: number;
  images: ProductImageInput[];
}

export interface ProductUpdate extends Omit<ProductCreate, "product_type"> { version: number }

export interface ProductView extends ProductCreate {
  id: string;
  images: ProductImageView[];
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Paginated<T> { items: T[]; total: number; page: number; page_size: number }
export type ProductPage = Paginated<ProductView>;
export interface ImageUploadView { url: string; size_bytes: number; mime_type: ImageMimeType }
