import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Plus, Pencil, Trash2 } from "lucide-react";
import apiClient from "@/lib/api-client";
import { Button } from "@/components/ui/button";
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { RoleFormDialog } from "./role-form-dialog";
import type { Role } from "@/types/role";
import type { RoleFormValues } from "./schemas";
import { SkeletonTable } from "@/components/skeletons/skeleton-table";

export function RolesSection() {
  const { t } = useTranslation("access-control");
  const queryClient = useQueryClient();
  const [editingRole, setEditingRole] = useState<Role | undefined>();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deletingRole, setDeletingRole] = useState<Role | null>(null);

  const { data: rolesData, isLoading } = useQuery<{ items: Role[]; num_found: number }>({
    queryKey: ["access-control", "roles"],
    queryFn: () =>
      apiClient
        .get<{ items: Role[]; num_found: number }>("/access-control/roles", {
          params: { page: 1, page_size: 100 },
        })
        .then((r) => r.data),
  });

  const roles = rolesData?.items ?? [];

  const createMutation = useMutation({
    mutationFn: (data: RoleFormValues) => apiClient.post("/access-control/roles", data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-control", "roles"] });
      setDialogOpen(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: RoleFormValues }) =>
      apiClient.put(`/access-control/roles/${id}`, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-control", "roles"] });
      setDialogOpen(false);
      setEditingRole(undefined);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.delete(`/access-control/roles/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["access-control", "roles"] });
      setDeletingRole(null);
    },
  });

  function handleSubmit(values: RoleFormValues) {
    if (editingRole) {
      updateMutation.mutate({ id: editingRole.id, data: values });
    } else {
      createMutation.mutate(values);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">{t("roles.title")}</h2>
        <Button
          onClick={() => {
            setEditingRole(undefined);
            setDialogOpen(true);
          }}
        >
          <Plus className="mr-2 h-4 w-4" />
          {t("roles.create")}
        </Button>
      </div>

      {isLoading ? (
        <SkeletonTable rows={3} columns={3} />
      ) : (
        <Table className="animate-fade-in">
          <TableHeader>
            <TableRow>
              <TableHead>{t("roles.fields.name")}</TableHead>
              <TableHead>{t("roles.fields.permissions")}</TableHead>
              <TableHead>{t("roles.fields.actions")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {roles.map((role) => (
              <TableRow key={role.id}>
                <TableCell className="font-medium">{role.name}</TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {role.permissions.map((p) => (
                      <Badge key={p} variant="outline">
                        {t(`permissions.${p}`)}
                      </Badge>
                    ))}
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        setEditingRole(role);
                        setDialogOpen(true);
                      }}
                      disabled={role.immutable}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeletingRole(role)}
                      disabled={role.protected || role.immutable}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      <RoleFormDialog
        open={dialogOpen}
        onClose={() => {
          setDialogOpen(false);
          setEditingRole(undefined);
        }}
        onSubmit={handleSubmit}
        role={editingRole}
      />

      <AlertDialog
        open={deletingRole !== null}
        onOpenChange={(open) => !open && setDeletingRole(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("common:confirm")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("roles.delete-confirm", { name: deletingRole?.name })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common:cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingRole && deleteMutation.mutate(deletingRole.id)}
            >
              {t("common:delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
