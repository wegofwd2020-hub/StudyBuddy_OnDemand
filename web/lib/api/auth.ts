import api from "./client";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export async function exchangeToken(idToken: string): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>("/auth/exchange", {
    id_token: idToken,
  });
  return res.data;
}

export async function exchangeTeacherToken(
  idToken: string,
): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>("/auth/teacher/exchange", {
    id_token: idToken,
  });
  return res.data;
}

export async function requestPasswordReset(email: string): Promise<void> {
  await api.post("/auth/forgot-password", { email });
}

export async function resetPassword(
  token: string,
  newPassword: string,
): Promise<void> {
  await api.post("/auth/reset-password", { token, new_password: newPassword });
}

export async function submitConsent(data: {
  student_id: string;
  parent_name: string;
  parent_email: string;
}): Promise<void> {
  await api.post("/auth/consent", data);
}
