import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { User } from "@/types/user";
import type { Role } from "@/types/role";

export function UsersSection() {
  const { t } = useTranslation("access-control");
  const queryClient = useQueryClient();

  const { data: users = [] } = useQuery<User[]>({
    queryKey: ["access-control", "users"],
    queryFn: () =>
      apiClient.get<User[]>("/access-control/users").then((r) => r.data),
  });

  const { data: roles = [] } = useQuery<Role[]>({
    queryKey: ["access-control", "roles"],
    queryFn: () =>
      apiClient.get<Role[]>("/access-control/roles").then((r) => r.data),
  });

  const assignMutation = useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: number }) =>
      apiClient.patch(`/access-control/users/${userId}/assign-role/${roleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-control", "users"] });
    },
  });

  const unassignMutation = useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: number }) =>
      apiClient.patch(`/access-control/users/${userId}/unassign-role/${roleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-control", "users"] });
    },
  });

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium">{t("users.title")}</h2>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("users.fields.email")}</TableHead>
            <TableHead>{t("users.fields.first-name")}</TableHead>
            <TableHead>{t("users.fields.last-name")}</TableHead>
            <TableHead>{t("users.fields.roles")}</TableHead>
            <TableHead>{t("common:actions")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map((user) => {
            const userRoleIds = user.roles.map((r) => r.id);
            const availableRoles = roles.filter(
              (r) => !userRoleIds.includes(r.id)
            );

            return (
              <TableRow key={user.id}>
                <TableCell>{user.email}</TableCell>
                <TableCell>{user.first_name}</TableCell>
                <TableCell>{user.last_name}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {user.roles.map((role) => (
                      <Badge
                        key={role.id}
                        variant="secondary"
                        className="cursor-pointer"
                        onClick={() =>
                          unassignMutation.mutate({
                            userId: user.id,
                            roleId: role.id,
                          })
                        }
                      >
                        {role.name} ×
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  {availableRoles.length > 0 && (
                    <Select
                      onValueChange={(roleId) =>
                        assignMutation.mutate({
                          userId: user.id,
                          roleId: Number(roleId),
                        })
                      }
                    >
                      <SelectTrigger className="w-[180px]">
                        <SelectValue placeholder={t("users.assign-role")} />
                      </SelectTrigger>
                      <SelectContent>
                        {availableRoles.map((role) => (
                          <SelectItem key={role.id} value={String(role.id)}>
                            {role.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
