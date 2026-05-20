import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Menu, ListTodo, Settings, Shield, Wrench } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { useHasPermission } from "@/hooks/use-permissions";
import { Permission } from "@/types/permission";

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
    labelKey: "common:menu.system",
    path: "/system",
    icon: Wrench,
    permission: Permission.ManageSystem,
  },
] as const;

export function MenuPanel() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { hasPermission } = useHasPermission();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <Menu className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {menuItems.map((item) => {
          const allowed = hasPermission(item.permission);
          if (allowed === false) return null;

          return (
            <DropdownMenuItem
              key={item.path}
              onClick={() => navigate(item.path)}
            >
              <item.icon className="mr-2 h-4 w-4" />
              {t(item.labelKey)}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
