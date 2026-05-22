import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Menu, ListTodo, Settings, Shield, Info, Wrench } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { useHasPermission } from "@/hooks/use-permissions";
import { Permission } from "@/types/permission";
import { SystemInfoDialog } from "@/features/system/system-info-dialog";

const menuItems = [
  {
    labelKey: "common:menu.tasks",
    path: "/tasks",
    icon: ListTodo,
    permission: Permission.ManageTasks,
  },
  {
    labelKey: "common:menu.settings",
    path: "/settings",
    icon: Settings,
    permission: { any: [Permission.ManageAppSettings, Permission.ManageTaskSettings] } as const,
  },
  {
    labelKey: "common:menu.access-control",
    path: "/access-control",
    icon: Shield,
    permission: Permission.ManageAccessControl,
  },
  {
    labelKey: "common:menu.maintenance",
    path: "/maintenance",
    icon: Wrench,
    permission: Permission.ManageAppSettings,
  },
] as const;

export function MenuPanel() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { hasPermission } = useHasPermission();
  const [showSystemInfo, setShowSystemInfo] = useState(false);

  const visibleItems = menuItems.filter((item) => hasPermission(item.permission) !== false);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon">
            <Menu className="h-5 w-5" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          {visibleItems.map((item) => (
            <DropdownMenuItem
              key={item.path}
              onClick={() => navigate(item.path)}
            >
              <item.icon className="mr-2 h-4 w-4" />
              {t(item.labelKey)}
            </DropdownMenuItem>
          ))}
          {visibleItems.length > 0 && <DropdownMenuSeparator />}
          <DropdownMenuItem onClick={() => setShowSystemInfo(true)}>
            <Info className="mr-2 h-4 w-4" />
            {t("common:menu.system")}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <SystemInfoDialog open={showSystemInfo} onClose={() => setShowSystemInfo(false)} />
    </>
  );
}
