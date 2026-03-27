import api from "./client";

export async function confirmEnrolment(token: string): Promise<{ school_name: string }> {
  const res = await api.post<{ school_name: string }>("/school/enrol/confirm", { token });
  return res.data;
}
