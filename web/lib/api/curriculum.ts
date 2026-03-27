import api from "./client";
import type { CurriculumTree } from "@/lib/types/api";

export async function getCurriculumTree(): Promise<CurriculumTree> {
  const res = await api.get<CurriculumTree>("/curriculum/tree");
  return res.data;
}
