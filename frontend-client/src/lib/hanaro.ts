// 하나로 SSO 공직자 판별 API 호출 + Clerk 유저 매핑 헬퍼 (서버 전용)
import { clerkClient } from "@clerk/nextjs/server";

export type OfficialCheckResult =
  | { ok: true; isOfficial: boolean }
  | { ok: false; reason: "invalid_credentials" | "rate_limited" | "server_config" | "upstream_error" };

const DEFAULT_URL = "https://hanaro.ffwp.or.kr/API_kim/officialLoginCheck2";

// 하나로 SSO 아이디/비밀번호를 서버에서 검증하고 공직자 여부를 받는다.
// keyValue/비밀번호는 절대 로깅하지 않는다.
export async function checkOfficial(userid: string, password: string): Promise<OfficialCheckResult> {
  const key = process.env.OFFICIAL_CHECK_KEY;
  const url = process.env.OFFICIAL_CHECK_URL ?? DEFAULT_URL;
  if (!key) return { ok: false, reason: "server_config" };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 8000);
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ keyValue: key, userid, password }),
      signal: controller.signal,
      cache: "no-store",
    });
    if (res.status === 429) return { ok: false, reason: "rate_limited" };
    const data = (await res.json().catch(() => null)) as
      | { authenticated?: boolean; isOfficial?: boolean; error?: string }
      | null;
    if (!data) return { ok: false, reason: "upstream_error" };
    if (data.error === "rate_limited") return { ok: false, reason: "rate_limited" };
    if (data.error === "invalid_key" || data.error === "missing_parameter")
      return { ok: false, reason: "server_config" };
    if (data.authenticated === true) return { ok: true, isOfficial: data.isOfficial === true };
    return { ok: false, reason: "invalid_credentials" };
  } catch {
    return { ok: false, reason: "upstream_error" };
  } finally {
    clearTimeout(timer);
  }
}

// 하나로 userid를 Clerk 유저에 idempotent하게 매핑한다(externalId 기준). isOfficial은 매 로그인 갱신.
export async function findOrCreateHanaroUser(userid: string, isOfficial: boolean): Promise<string> {
  const client = await clerkClient();
  const extId = `hanaro:${userid}`;
  const existing = await client.users.getUserList({ externalId: [extId], limit: 1 });
  if (existing.totalCount > 0) {
    const u = existing.data[0];
    await client.users.updateUserMetadata(u.id, {
      publicMetadata: { ...u.publicMetadata, isOfficial, provider: "hanaro", hanaroUserId: userid },
    });
    return u.id;
  }
  try {
    const created = await client.users.createUser({
      externalId: extId,
      emailAddress: [`${userid}@hanaro.local`],
      skipPasswordRequirement: true,
      publicMetadata: { isOfficial, provider: "hanaro", hanaroUserId: userid },
    });
    return created.id;
  } catch (e) {
    // 동시 최초 로그인 race — 이미 생성됐으면 재조회
    const retry = await client.users.getUserList({ externalId: [extId], limit: 1 });
    if (retry.totalCount > 0) return retry.data[0].id;
    throw e;
  }
}
