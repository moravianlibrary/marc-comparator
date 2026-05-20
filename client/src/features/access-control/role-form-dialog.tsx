import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { roleSchema, type RoleFormValues } from "./schemas";
import { Permission } from "@/types/permission";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import type { Role } from "@/types/role";

interface RoleFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (values: RoleFormValues) => void;
  role?: Role;
}

const ALL_PERMISSIONS = Object.values(Permission);

export function RoleFormDialog({ open, onClose, onSubmit, role }: RoleFormDialogProps) {
  const { t } = useTranslation("access-control");

  const form = useForm<RoleFormValues>({
    resolver: zodResolver(roleSchema),
    defaultValues: role
      ? { name: role.name, permissions: role.permissions }
      : { name: "", permissions: [] },
  });

  useEffect(() => {
    if (open) {
      form.reset(
        role
          ? { name: role.name, permissions: role.permissions }
          : { name: "", permissions: [] }
      );
    }
  }, [open, role, form]);

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {role ? t("roles.edit") : t("roles.create")}
          </DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("roles.fields.name")}</FormLabel>
                  <FormControl>
                    <Input {...field} disabled={role?.immutable} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="permissions"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("roles.fields.permissions")}</FormLabel>
                  <div className="grid grid-cols-2 gap-2">
                    {ALL_PERMISSIONS.map((perm) => (
                      <label key={perm} className="flex items-center gap-2">
                        <Checkbox
                          checked={field.value.includes(perm)}
                          disabled={role?.immutable}
                          onCheckedChange={(checked) => {
                            if (checked) {
                              field.onChange([...field.value, perm]);
                            } else {
                              field.onChange(
                                field.value.filter((p) => p !== perm)
                              );
                            }
                          }}
                        />
                        <span className="text-sm">
                          {t(`permissions.${perm}`)}
                        </span>
                      </label>
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                {t("common:cancel")}
              </Button>
              <Button type="submit" disabled={role?.immutable}>
                {t("common:save")}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
