import { apiClient } from "@/lib/api-client";
import { type DashboardData } from "./schemas";

export const dashboardKeys = {
  all: ["dashboard"] as const,
  stats: (days: number, fbPage?: number) => [...dashboardKeys.all, "stats", days, fbPage] as const,
};

export async function getDashboardStats(days: number = 30, fbPage: number = 1, fbSize: number = 10): Promise<DashboardData> {
  const { data } = await apiClient.get<DashboardData>(`/api/v1/admin/dashboard/stats?days=${days}&fb_page=${fbPage}&fb_size=${fbSize}`);
  return data;
}
