import { useTheme } from "next-themes";

interface AppLogoProps {
  className?: string;
}

export function AppLogo({ className = "mx-auto mb-4 h-16 w-auto" }: AppLogoProps) {
  const { resolvedTheme } = useTheme();

  return (
    <img
      src={
        resolvedTheme === "dark"
          ? "/marcomparator-logo-transparent.png"
          : "/marcomparator-logo-dark-text-transparent.png"
      }
      alt="MARC Comparator"
      className={className}
    />
  );
}
