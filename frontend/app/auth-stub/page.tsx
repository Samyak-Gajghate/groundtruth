"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { setToken } from "@/lib/api";

export default function AuthStub() {
  const router = useRouter();
  const sp = useSearchParams();
  useEffect(() => {
    const t = sp?.get("token");
    const next = sp?.get("next") || "/dashboard";
    if (t) {
      setToken(t);
      router.replace(next);
    }
  }, [router, sp]);
  return null;
}
