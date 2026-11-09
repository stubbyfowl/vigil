import { useData } from "./app";
import type { Member } from "../api/types";

export function useCrew(): Member[] {
  return useData<{ crew: Member[] }>("/api/crew").data?.crew ?? [];
}
