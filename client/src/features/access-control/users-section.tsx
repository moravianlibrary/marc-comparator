import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import apiClient from "@/lib/api-client";
import { useGetMe } from "@/hooks/use-auth";
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
import { SkeletonTable } from "@/components/skeletons/skeleton-table";

export function UsersSection() {
  const { t } = useTranslation("access-control");
  const queryClient = useQueryClient();
  const { data: me } = useGetMe();

  const { data: usersData, isLoading } = useQuery<{ items: User[]; num_found: number }>({
    queryKey: ["access-control", "users"],
    queryFn: () =>
      apiClient
        .get<{ items: User[]; num_found: number }>(
          "/access-control/users",
          {
            params: { page: 1, page_size: 100 },
          },
        )
        .then((r) => r.data),
  });

  const { data: rolesData } = useQuery<{ items: Role[]; num_found: number }>({
    queryKey: ["access-control", "roles"],
    queryFn: () =>
      apiClient
        .get<{ items: Role[]; num_found: number }>(
          "/access-control/roles",
          {
            params: { page: 1, page_size: 100 },
          },
        )
        .then((r) => r.data),
  });

  const users = usersData?.items ?? [];
  const roles = rolesData?.items ?? [];

  const assignMutation = useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: number }) =>
      apiClient.patch(
        `/access-control/users/${userId}/assign-role/${roleId}`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["access-control", "users"],
      });
    },
  });

  const unassignMutation = useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: number }) =>
      apiClient.patch(
        `/access-control/users/${userId}/unassign-role/${roleId}`,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["access-control", "users"],
      });
    },
  });

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-medium">{t("users.title")}</h2>

      {isLoading ? (
        <SkeletonTable rows={4} columns={5} />
      ) : (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("users.fields.email")}</TableHead>
            <TableHead>{t("users.fields.first-name")}</TableHead>
            <TableHead>{t("users.fields.last-name")}</TableHead>
            <TableHead>{t("users.fields.roles")}</TableHead>
            <TableHead>{t("users.assign-role")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map((user) => {
            const isSelf = me?.id === user.id;
            const userRoleIds = user.roles.map((r) => r.id);
            const availableRoles = roles.filter(
              (r) => !userRoleIds.includes(r.id),
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
                        variant={
                          isSelf
                            ? "outline"
                            : "secondary"
                        }
                        className={
                          isSelf
                            ? ""
                            : "cursor-pointer"
                        }
                        onClick={
                          isSelf
                            ? undefined
                            : () =>
                                unassignMutation.mutate(
                                  {
                                    userId: user.id,
                                    roleId: role.id,
                                  },
                                )
                        }
                      >
                        {role.name}
                        {!isSelf && " ×"}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  {!isSelf && availableRoles.length > 0 && (
                    <Select
                      onValueChange={(roleId) =>
                        assignMutation.mutate({
                          userId: user.id,
                          roleId: Number(roleId),
                        })
                      }
                    >
                      <SelectTrigger className="w-[180px]">
                        <SelectValue
                          placeholder={t(
                            "users.assign-role",
                          )}
                        />
                      </SelectTrigger>
                      <SelectContent>
                        {availableRoles.map((role) => (
                          <SelectItem
                            key={role.id}
                            value={String(role.id)}
                          >
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
      )}
    </div>
  );
}
