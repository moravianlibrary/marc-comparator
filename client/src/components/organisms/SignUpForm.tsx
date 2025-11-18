import { z } from "zod";
import {
    Form,
    FormGroup,
    TextInput,
    Button,
    FormHelperText,
    HelperText,
    HelperTextItem,
    ActionGroup,
} from "@patternfly/react-core";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import { ExclamationCircleIcon } from "@patternfly/react-icons";
import type { ReactElement } from "react";

// --- Zod schema for registration form ---
const SignUpFormDataSchema = z
    .object({
        email: z.email({ message: "Invalid email" }),
        first_name: z.string().min(1, { message: "First name is required" }),
        last_name: z.string().min(1, { message: "Last name is required" }),
        password: z
            .string()
            .min(8, { message: "Password must be at least 8 characters" }),
        confirm_password: z.string(),
    })
    .refine((data) => data.password === data.confirm_password, {
        message: "Passwords do not match",
        path: ["confirm_password"],
    });

export type SignUpFormData = z.infer<typeof SignUpFormDataSchema>;

const SignUpForm = ({
    onSubmit,
    isPending,
}: {
    onSubmit: (data: SignUpFormData) => void;
    isPending?: boolean;
}): ReactElement => {
    const {
        control,
        handleSubmit,
        formState: { errors, isSubmitted },
    } = useForm<SignUpFormData>({
        resolver: zodResolver(SignUpFormDataSchema),
        defaultValues: {
            email: "",
            first_name: "",
            last_name: "",
            password: "",
            confirm_password: "",
        },
    });

    const renderTextInput = (fieldName: string, field: any, errors: any) => (
        <TextInput
            {...field}
            id={fieldName}
            type="text"
            validated={
                errors?.[fieldName]?.message
                    ? "error"
                    : isSubmitted
                    ? "success"
                    : undefined
            }
        />
    );

    const renderPasswordInput = (
        fieldName: string,
        field: any,
        errors: any
    ) => (
        <TextInput
            {...field}
            id={fieldName}
            type="password"
            validated={
                errors?.[fieldName]?.message
                    ? "error"
                    : isSubmitted
                    ? "success"
                    : undefined
            }
        />
    );

    const renderErrorText = (fieldName: string, errors: any) => {
        if (errors?.[fieldName]?.message) {
            return (
                <FormHelperText>
                    <HelperText>
                        <HelperTextItem
                            icon={<ExclamationCircleIcon />}
                            variant="error"
                        >
                            {errors?.[fieldName]?.message}
                        </HelperTextItem>
                    </HelperText>
                </FormHelperText>
            );
        }
        return null;
    };

    return (
        <Form onSubmit={handleSubmit((data) => !isPending && onSubmit(data))}>
            <FormGroup label="Email" isRequired fieldId="email">
                <Controller
                    name="email"
                    control={control}
                    render={({ field }) =>
                        renderTextInput("email", field, errors)
                    }
                />
                {renderErrorText("email", errors)}
            </FormGroup>
            <FormGroup label="First Name" isRequired fieldId="first_name">
                <Controller
                    name="first_name"
                    control={control}
                    render={({ field }) =>
                        renderTextInput("first_name", field, errors)
                    }
                />
                {renderErrorText("first_name", errors)}
            </FormGroup>
            <FormGroup label="Last Name" isRequired fieldId="last_name">
                <Controller
                    name="last_name"
                    control={control}
                    render={({ field }) =>
                        renderTextInput("last_name", field, errors)
                    }
                />
                {renderErrorText("last_name", errors)}
            </FormGroup>
            <FormGroup label="Password" isRequired fieldId="password">
                <Controller
                    name="password"
                    control={control}
                    render={({ field }) =>
                        renderPasswordInput("password", field, errors)
                    }
                />
                {renderErrorText("password", errors)}
            </FormGroup>
            <FormGroup
                label="Confirm Password"
                isRequired
                fieldId="confirm_password"
            >
                <Controller
                    name="confirm_password"
                    control={control}
                    render={({ field }) =>
                        renderPasswordInput("confirm_password", field, errors)
                    }
                />
                {renderErrorText("confirm_password", errors)}
            </FormGroup>

            <ActionGroup>
                <Button
                    type="submit"
                    variant="primary"
                    isBlock
                    isLoading={isPending}
                >
                    Register
                </Button>
            </ActionGroup>
        </Form>
    );
};

export default SignUpForm;
