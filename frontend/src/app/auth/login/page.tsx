// frontend/src/app/auth/login/page.tsx

import type { Metadata } from "next";
import LoginPageClient from "./LoginPageClient";

export const metadata: Metadata = {
  title: "Sign In",
  description: "Sign in to CI Healer with your GitHub account.",
  robots: { index: false, follow: false },
};

export default function LoginPage() {
  return <LoginPageClient />;
}
