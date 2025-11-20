import React from "react";
import {
    useForm,
    Controller,
    useFieldArray,
    type FieldValues,
    type UseFormRegister,
    type DefaultValues,
    type Path,
    type UseControllerProps,
    type UseFieldArrayRemove,
    type ControllerRenderProps,
    type ControllerFieldState,
    type UseFormStateReturn,
    get,
    type FieldErrors,
    type Resolver,
} from "react-hook-form";
import {
    ZodObject,
    ZodEnum,
    ZodArray,
    ZodOptional,
    ZodType,
    ZodNullable,
    ZodString,
    ZodNumber,
    ZodBoolean,
    ZodDefault,
} from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
    Button,
    FormGroup,
    HelperText,
    HelperTextItem,
    Form,
    Switch,
    TextInput,
    FormFieldGroupExpandable,
    FormFieldGroupHeader,
    FormHelperText,
    Split,
    SplitItem,
} from "@patternfly/react-core";
import { TrashIcon } from "@patternfly/react-icons";

export interface ZodFormProps<T extends FieldValues> {
    schema: ZodType<T, any, any>;
    defaultValues?: DefaultValues<T>;
    onSubmit?: (data: T) => void;
}

type AnyZod = ZodType<unknown>;

interface FieldProps<T extends FieldValues, S extends AnyZod>
    extends UseControllerProps<T> {
    schema: S;
    register?: UseFormRegister<T>;
    errors: FieldErrors<T>;
    isRequired?: boolean;
    remove?: UseFieldArrayRemove;
}

const RemoveButton = ({ onClick }: { onClick: () => void }) => (
    <Button variant="link" isDanger icon={<TrashIcon />} onClick={onClick} />
);

function normalizeToI18nKey(name: string): string {
    return `form.${name.replace(/\.\d+\./g, ".").replace(/\.\d+$/g, "")}`;
}

const VALUE_FIELD_RENDERER_MAP: Record<
    string,
    <T extends FieldValues>(props: {
        field: ControllerRenderProps<T, Path<T>>;
        fieldState: ControllerFieldState;
        formState: UseFormStateReturn<T>;
    }) => React.ReactElement
> = {
    ZodString: ({ field, fieldState }) => (
        <TextInput
            {...field}
            id={field.name}
            type="text"
            value={field.value ?? ""}
            onChange={(_, v) => field.onChange((v as unknown) ?? "")}
            validated={fieldState.error ? "error" : "success"}
        />
    ),
    ZodNumber: ({ field, fieldState }) => (
        <TextInput
            {...field}
            id={field.name}
            type="number"
            value={field.value ?? ""}
            onChange={(_, v) => {
                const asNum = (v as unknown) === "" ? undefined : Number(v);
                field.onChange(asNum);
            }}
            validated={fieldState.error ? "error" : "success"}
        />
    ),
    ZodBoolean: ({ field }) => (
        <Switch
            id={field.name}
            isChecked={!!field.value}
            onChange={(_, v: boolean) => field.onChange(v)}
            label={String(field.value)}
        />
    ),
};

const ValueField = <
    T extends FieldValues,
    S extends ZodString | ZodNumber | ZodBoolean
>(
    props: FieldProps<T, S>
) => {
    const error = get(props.errors, props.name);
    return (
        <FormGroup
            label={normalizeToI18nKey(props.name)}
            fieldId={props.name}
            isRequired={props.isRequired}
        >
            <Split>
                <SplitItem isFilled>
                    <Controller
                        {...props}
                        render={
                            VALUE_FIELD_RENDERER_MAP[
                                props.schema.constructor.name
                            ]
                        }
                    />
                </SplitItem>
                <SplitItem>
                    {props.remove && (
                        <RemoveButton
                            onClick={() =>
                                props.remove!(
                                    Number(props.name.split(".").pop())
                                )
                            }
                        />
                    )}
                </SplitItem>
            </Split>
            {error?.message && (
                <FormHelperText>
                    <HelperText>
                        <HelperTextItem variant="error">
                            {String(error.message)}
                        </HelperTextItem>
                    </HelperText>
                </FormHelperText>
            )}
        </FormGroup>
    );
};

function getNewItemValue(schema: AnyZod): any {
    if (schema instanceof ZodDefault) {
        return schema.def.defaultValue;
    }
    if (schema instanceof ZodObject) {
        const shape = (schema as ZodObject<any>).shape;
        const obj: any = {};
        for (const key in shape) {
            obj[key] = getNewItemValue((shape as any)[key]);
        }
        return obj;
    }
    if (schema instanceof ZodArray) {
        return [];
    }
    if (schema instanceof ZodString) return "";
    if (schema instanceof ZodNumber) return 0;
    if (schema instanceof ZodBoolean) return false;
    if (schema instanceof ZodEnum) return (schema as any).options?.[0] ?? "";
    if (schema instanceof ZodOptional || schema instanceof ZodNullable) {
        return getNewItemValue(
            (schema as any)._def?.innerType ?? (schema as any)._def?.innerType
        );
    }
    return null;
}

const RenderField = <T extends FieldValues>(props: FieldProps<T, AnyZod>) => {
    const { name, control, register } = props;

    let schema = props.schema;

    // Unwrap wrappers
    if (
        schema instanceof ZodOptional ||
        schema instanceof ZodNullable ||
        schema instanceof ZodDefault
    ) {
        schema = schema.def.innerType as AnyZod;
    }

    // Primitive values
    if (
        schema instanceof ZodString ||
        schema instanceof ZodNumber ||
        schema instanceof ZodBoolean
    ) {
        return <ValueField {...props} schema={schema} />;
    }

    // Object
    if (schema instanceof ZodObject) {
        return (
            <FormFieldGroupExpandable
                toggleAriaLabel={`Toggle ${name} section`}
                header={
                    <Split>
                        <SplitItem isFilled>
                            <FormFieldGroupHeader
                                titleText={{
                                    text:
                                        normalizeToI18nKey(props.name) +
                                        ".title",
                                    id: `${name}-header`,
                                }}
                            />
                        </SplitItem>
                        <SplitItem>
                            {props.remove && (
                                <RemoveButton
                                    onClick={() =>
                                        props.remove!(
                                            Number(name.split(".").pop())
                                        )
                                    }
                                />
                            )}
                        </SplitItem>
                    </Split>
                }
            >
                {Object.entries(schema.shape).map(([key, subschema]) => (
                    <RenderField
                        key={key}
                        name={`${name}.${key}` as Path<T>}
                        schema={subschema}
                        control={control}
                        register={register}
                        errors={props.errors}
                    />
                ))}
            </FormFieldGroupExpandable>
        );
    }

    // Array
    if (schema instanceof ZodArray) {
        const arrSchema = schema as ZodArray<any>;
        const { fields, append, remove } = useFieldArray({
            name: name as any,
            control,
        });

        return (
            <FormFieldGroupExpandable
                header={
                    <FormFieldGroupHeader
                        titleText={{
                            text: normalizeToI18nKey(props.name) + ".title",
                            id: `${name}-header`,
                        }}
                        actions={
                            <>
                                <Button
                                    variant="link"
                                    isDanger
                                    onClick={() => remove()}
                                >
                                    Delete all
                                </Button>
                                <Button
                                    variant="secondary"
                                    onClick={() =>
                                        append(
                                            getNewItemValue(arrSchema.element)
                                        )
                                    }
                                >
                                    Add item
                                </Button>
                            </>
                        }
                    />
                }
            >
                {fields.map((_, index) => (
                    <RenderField
                        key={index}
                        {...props}
                        name={`${name}.${index}` as Path<T>}
                        schema={arrSchema.element}
                        errors={props.errors}
                        remove={remove}
                    />
                ))}
            </FormFieldGroupExpandable>
        );
    }

    return (
        <HelperText>
            <HelperTextItem variant="error">
                Unsupported field type: {schema.constructor.name}
            </HelperTextItem>
        </HelperText>
    );
};

export const ZodForm = <T extends FieldValues>({
    schema,
    defaultValues,
    onSubmit,
}: ZodFormProps<T>) => {
    if (!(schema instanceof ZodObject)) {
        throw new Error("ZodForm only supports ZodObject schemas at the root");
    }

    const {
        control,
        register,
        handleSubmit,
        formState: { errors },
    } = useForm<T>({
        resolver: zodResolver(schema) as Resolver<T>,
        defaultValues,
        mode: "onChange",
    });

    const handleFormSubmit = (data: T) => {
        if (onSubmit) onSubmit(data);
        else console.log("Form submitted:", data);
    };
    console.log("Form errors:", errors);

    return (
        <Form onSubmit={handleSubmit(handleFormSubmit)}>
            {Object.entries(schema.shape).map(([key, subschema]) => (
                <RenderField
                    key={key}
                    name={key as Path<T>}
                    schema={subschema}
                    control={control}
                    register={register}
                    errors={errors}
                />
            ))}
        </Form>
    );
};

export default ZodForm;
