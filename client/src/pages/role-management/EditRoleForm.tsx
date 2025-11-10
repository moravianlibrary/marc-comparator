import {
    ActionGroup,
    Button,
    Checkbox,
    Form,
    FormGroup,
    FormHelperText,
    HelperText,
    HelperTextItem,
    Stack,
    StackItem,
    Switch,
    TextInput,
    Title,
} from "@patternfly/react-core";
import { useState, type ReactElement } from "react";
import { type EditRole } from "../../models/api/requests/roles";
import {
    type Permission,
    PermissionDependencies,
    PermissionSchema,
} from "../../models/primitives/permissions";

function getAllPermissionDependencies(permission: Permission): Permission[] {
    const direct = PermissionDependencies[permission] || [];
    const indirect = direct.flatMap(getAllPermissionDependencies);
    return Array.from(new Set([...direct, ...indirect]));
}

function removeDependents(
    selected: Permission[],
    removed: Permission
): Permission[] {
    const dependents = Object.entries(PermissionDependencies)
        .filter(([_, deps]) => deps.includes(removed))
        .map(([perm]) => perm as Permission);

    let updated = selected.filter((p) => p !== removed);
    dependents.forEach((dep) => {
        if (updated.includes(dep)) {
            updated = removeDependents(updated, dep);
        }
    });
    return updated;
}

interface EditRoleFormProps {
    initialData: EditRole;
    isProtected?: boolean;
    onSubmit: (data: EditRole) => void;
    onCancel?: () => void;
    isSubmitting?: boolean;
}

const EditRoleForm = ({
    initialData,
    isProtected = false,
    onSubmit,
    onCancel,
    isSubmitting = false,
}: EditRoleFormProps): ReactElement => {
    const [name, setName] = useState(initialData?.name || "");
    const [permissions, setPermissions] = useState<Permission[]>(
        initialData?.permissions || []
    );
    const [nameError, setNameError] = useState<string | null>(null);

    const handlePermissionChange = (perm: Permission, checked: boolean) => {
        setPermissions((prev) => {
            if (checked) {
                const deps = getAllPermissionDependencies(perm);
                return Array.from(new Set([...prev, perm, ...deps]));
            } else {
                return removeDependents(prev, perm);
            }
        });
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();

        if (name.trim().length < 4) {
            setNameError("Role name must be at least 4 characters long");
            return;
        }

        onSubmit({ name, permissions });
    };

    return (
        <Form onSubmit={handleSubmit}>
            <Title headingLevel="h2" size="lg">
                {initialData ? "Edit Role" : "Create Role"}
            </Title>

            <FormGroup label="Role name" isRequired fieldId="role-name">
                <TextInput
                    id="role-name"
                    name="role-name"
                    value={name}
                    onChange={(_, val) => {
                        setName(val);
                        setNameError(null);
                    }}
                    isRequired
                    validated={nameError ? "error" : "default"}
                    isDisabled={isProtected}
                />
                {nameError && (
                    <FormHelperText>
                        <HelperText>
                            <HelperTextItem variant="error">
                                {nameError}
                            </HelperTextItem>
                        </HelperText>
                    </FormHelperText>
                )}
            </FormGroup>

            <FormGroup label="Permissions" fieldId="permissions-group">
                <Stack hasGutter>
                    {PermissionSchema.options.map((perm) => (
                        <StackItem key={perm}>
                            <Switch
                                key={perm}
                                id={`perm-${perm}`}
                                label={perm}
                                isChecked={permissions.includes(perm)}
                                onChange={(_, checked) =>
                                    handlePermissionChange(perm, checked)
                                }
                            />
                        </StackItem>
                    ))}
                </Stack>
            </FormGroup>

            <ActionGroup>
                <Button
                    type="submit"
                    variant="primary"
                    isDisabled={isSubmitting}
                    isLoading={isSubmitting}
                >
                    {initialData ? "Save Changes" : "Create Role"}
                </Button>
                {onCancel && (
                    <Button
                        variant="link"
                        onClick={onCancel}
                        className="pf-v5-u-ml-md"
                        isDisabled={isSubmitting}
                    >
                        Cancel
                    </Button>
                )}
            </ActionGroup>
        </Form>
    );
};

export default EditRoleForm;
