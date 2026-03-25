"use client";

import { useUser, useAuth } from "@clerk/nextjs";

export function useAuthStore() {
  const { user, isLoaded } = useUser();
  const { signOut } = useAuth();

  return {
    user: user
      ? {
          email: user.primaryEmailAddress?.emailAddress,
          user_metadata: {
            name: user.fullName,
            avatar_url: user.imageUrl,
          },
        }
      : null,
    isLoading: !isLoaded,
    isAuthenticated: !!user,
    initialize: async () => {},
    signOut: () => signOut(),
  };
}
