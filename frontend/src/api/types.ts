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
