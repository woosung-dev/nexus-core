// 하나로 세션 쿠키 이름과 사용자 타입 (middleware 의 edge 런타임에서도 안전하도록 상수만 둔다)

export const SESSION_COOKIE = "nexus_session";

export type SessionUser = {
  userid: string;
  email: string;
  isOfficial: boolean;
};
