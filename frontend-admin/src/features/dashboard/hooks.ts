import { useQuery } from "@tanstack/react-query";
import { dashboardKeys, getDashboardStats } from "./api";

export function useDashboardStats(days: number = 30, fbPage: number = 1, fbSize: number = 10) {
  return useQuery({
    queryKey: dashboardKeys.stats(days, fbPage),
    queryFn: () => getDashboardStats(days, fbPage, fbSize),
  });
}
