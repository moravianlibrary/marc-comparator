import { useTranslation } from "react-i18next";
import { ALargeSmall } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useFontSize, FONT_SIZE_OPTIONS, type FontSizeKey } from "@/hooks/use-font-size";

export function FontSizeControl() {
  const { t } = useTranslation("common");
  const { size, setSize } = useFontSize();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <ALargeSmall className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuRadioGroup value={size} onValueChange={(v) => setSize(v as FontSizeKey)}>
          {FONT_SIZE_OPTIONS.map((key) => (
            <DropdownMenuRadioItem key={key} value={key}>
              {t(`font-size.${key}`)}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
