import { useEffect } from "react";
import { useLogout } from "@/hooks/use-auth";

export function LogoutPage() {
  const logout = useLogout();

  useEffect(() => {
    logout.mutate();
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-muted-foreground">Odhlašování...</div>
    </div>
  );
}
