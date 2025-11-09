import TimesIcon from "@patternfly/react-icons/dist/esm/icons/times-icon";

import {
    useForm,
    useFieldArray,
    type Control,
    type FieldValues,
    type UseFormRegister,
    type FieldErrors,
    type DefaultValues,
    Controller,
} from "react-hook-form";
import z, {
    ZodObject,
    ZodEnum,
    ZodArray,
    ZodOptional,
    ZodType,
    ZodNullable,
    ZodDefault,
    ZodUnion,
    ZodNull,
    ZodString,
    ZodNumber,
    ZodBoolean,
    ZodNonOptional,
    ZodRecord,
} from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
    Button,
    Card,
    CardBody,
    CardExpandableContent,
    CardFooter,
    CardHeader,
    CardTitle,
    DescriptionList,
    DescriptionListDescription,
    DescriptionListGroup,
    DescriptionListTerm,
    DescriptionListTermHelpText,
    DescriptionListTermHelpTextButton,
    Grid,
    HelperText,
    HelperTextItem,
    InputGroup,
    InputGroupItem,
    Label,
    MenuToggle,
    type MenuToggleElement,
    Popover,
    Select,
    SelectOption,
    Stack,
    StackItem,
    Switch,
    TextInput,
} from "@patternfly/react-core";
import { Children, Fragment, useState } from "react";
import React from "react";

export interface ZodFormProps<T extends FieldValues> {
    schema: ZodType<T, any, any>;
    defaultValues?: DefaultValues<T>;
    onSubmit?: (data: T) => void;
}

interface FieldRendererProps<T extends FieldValues, S extends ZodType> {
    name: string;
    schema: S;
    control: Control<T>;
    register: UseFormRegister<T>;
    errors: FieldErrors<T>;
}

interface FieldContainerProps<T extends FieldValues, S extends ZodType> {
    name: string;
    schema: S;
    children: React.ReactNode;
}

interface ZodFormFieldProps<T extends FieldValues, S extends ZodType> {
    name: string;
    schema: S;
    control: Control<T>;
    register: UseFormRegister<T>;
    errors: FieldErrors<T>;
    isRoot?: boolean;
    arrayItem?: boolean;
}

const FieldError = <T extends FieldValues>({
    errors,
}: {
    errors: FieldErrors<T>;
}) =>
    errors?.message ? (
        <HelperText>
            <HelperTextItem variant="error">
                {String(errors.message)}
            </HelperTextItem>
        </HelperText>
    ) : null;

const FieldContainer = <T extends FieldValues, S extends ZodType>({
    name,
    schema,
    children,
}: FieldContainerProps<T, S>) => (
    <DescriptionListGroup>
        {schema.description ? (
            <DescriptionListTermHelpText>
                <Popover headerContent={name} bodyContent={schema.description}>
                    <DescriptionListTermHelpTextButton>
                        {name}
                    </DescriptionListTermHelpTextButton>
                </Popover>
            </DescriptionListTermHelpText>
        ) : (
            <DescriptionListTerm>{name}</DescriptionListTerm>
        )}
        <DescriptionListDescription>
            <Stack hasGutter>
                {Children.map(children, (child, index) => (
                    <StackItem key={index}>{child}</StackItem>
                ))}
            </Stack>
        </DescriptionListDescription>
    </DescriptionListGroup>
);

const SectionContainer = ({
    name,
    children,
}: {
    name: string;
    children: React.ReactNode;
}) => {
    const [isExpanded, setIsExpanded] = useState<boolean>(true);

    return (
        <Card isExpanded={isExpanded} isCompact>
            <CardHeader onExpand={() => setIsExpanded(!isExpanded)}>
                <CardTitle>{name}</CardTitle>
            </CardHeader>
            <CardExpandableContent>
                <CardBody>{children}</CardBody>
            </CardExpandableContent>
        </Card>
    );
};

const StringField = <T extends FieldValues>({
    name,
    schema,
    control,
    errors,
}: FieldRendererProps<T, ZodString>) => (
    <FieldContainer name={name} schema={schema}>
        <Controller
            name={name as any}
            control={control}
            render={({ field }) => (
                <TextInput
                    {...field}
                    type="text"
                    validated={errors?.message ? "error" : "success"}
                />
            )}
        />
        <FieldError errors={errors} />
    </FieldContainer>
);

const NumberField = <T extends FieldValues>({
    name,
    schema,
    control,
    errors,
}: FieldRendererProps<T, ZodNumber>) => (
    <FieldContainer name={name} schema={schema}>
        <Controller
            name={name as any}
            control={control}
            render={({ field }) => (
                <TextInput
                    {...field}
                    type="number"
                    validated={errors?.message ? "error" : "success"}
                />
            )}
        />
        <FieldError errors={errors} />
    </FieldContainer>
);

const BooleanField = <T extends FieldValues>({
    name,
    schema,
    control,
    errors,
}: FieldRendererProps<T, ZodBoolean>) => (
    <FieldContainer name={name} schema={schema}>
        <Controller
            name={name as any}
            control={control}
            render={({ field }) => (
                <Switch
                    {...field}
                    isChecked={field.value}
                    onChange={field.onChange}
                    label={name}
                />
            )}
        />
        <FieldError errors={errors} />
    </FieldContainer>
);

const EnumField = <T extends FieldValues>({
    name,
    schema,
    control,
    register,
    errors,
}: FieldRendererProps<T, ZodEnum<any>>) => {
    const [isOpen, setIsOpen] = useState(false);

    const toggle = (toggleRef: React.Ref<MenuToggleElement>) => (
        <MenuToggle
            ref={toggleRef}
            // onClick={onToggleClick}
            isExpanded={isOpen}
            style={
                {
                    width: "200px",
                } as React.CSSProperties
            }
        >
            {/* {selected} */}
        </MenuToggle>
    );

    return (
        <FieldContainer name={name} schema={schema}>
            <Controller
                name={name as any}
                control={control}
                render={({ field }) => (
                    <Select
                        {...field}
                        isOpen={isOpen}
                        onOpenChange={setIsOpen}
                        toggle={toggle}
                    >
                        {schema.options.map((opt) => (
                            <SelectOption key={opt} value={opt}>
                                {opt}
                            </SelectOption>
                        ))}
                    </Select>
                )}
            />
            <FieldError errors={errors} />
        </FieldContainer>
    );
};

const ObjectField = <T extends FieldValues>({
    name,
    schema,
    control,
    register,
    errors,
}: FieldRendererProps<T, ZodObject<any>>) => (
    <SectionContainer name={name}>
        <DescriptionList>
            {Object.entries(schema.shape).map(([key, subschema]) => (
                <RenderField
                    key={key}
                    name={`${name}.${key}`}
                    schema={subschema}
                    control={control}
                    register={register}
                    errors={errors?.[key] || ({} as any)}
                />
            ))}
        </DescriptionList>
    </SectionContainer>
);

const ArrayField = <T extends FieldValues>({
    name,
    schema,
    control,
    register,
    errors,
}: FieldRendererProps<T, ZodArray<any>>) => {
    const { fields, append, remove } = useFieldArray({
        name,
        control,
    });
    const content = (
        <Fragment>
            {fields.map((field, index) => (
                <RenderField
                    key={field.id}
                    name={`${name}[${index}]`}
                    schema={schema.element as ZodType<any>}
                    control={control}
                    register={register}
                    errors={errors?.[index] || ({} as any)}
                />
            ))}
            <Label
                color="blue"
                onClick={() =>
                    append(
                        (schema.element instanceof ZodObject
                            ? {}
                            : schema.element instanceof ZodArray
                            ? []
                            : "") as any
                    )
                }
            >
                Add item
            </Label>
        </Fragment>
    );

    return schema.element instanceof ZodString ||
        schema.element instanceof ZodNumber ? (
        <FieldContainer name={name} schema={schema}>
            {content}
        </FieldContainer>
    ) : (
        <SectionContainer name={name}>{content}</SectionContainer>
    );
};

const RecordField = <T extends FieldValues>({
    name,
    schema,
    control,
    register,
    errors,
}: FieldRendererProps<T, ZodRecord<any, any>>) => {
    const { fields, append, remove } = useFieldArray({
        control,
        name: name as any,
    });

    const keyType = schema.def.valueType ? schema.def.keyType : z.string();
    const valueType = schema.def.valueType ?? schema.def.keyType;

    if (
        !(
            keyType instanceof ZodString ||
            keyType instanceof ZodNumber ||
            keyType instanceof ZodEnum
        )
    ) {
        return (
            <HelperText>
                <HelperTextItem variant="error">
                    Unsupported record key type: {keyType.constructor.name} for
                    field "{name}"
                </HelperTextItem>
            </HelperText>
        );
    }

    return (
        <FieldContainer name={name} schema={schema}>
            {fields.map((field, index) => (
                <SectionContainer key={field.id} name={`Item ${index + 1}`}>
                    <RenderField
                        key={field.id}
                        name={`${name}[${index}]`}
                        schema={valueType as ZodType<any>}
                        control={control}
                        register={register}
                        errors={errors?.[index] || ({} as any)}
                    />
                </SectionContainer>
            ))}
            <Label
                color="blue"
                onClick={() =>
                    append(
                        (valueType instanceof ZodObject
                            ? {}
                            : valueType instanceof ZodArray
                            ? []
                            : "") as any
                    )
                }
            >
                Add item
            </Label>
        </FieldContainer>
    );
};

const InnerField = <T extends FieldValues>({
    schema,
    ...rest
}: ZodFormFieldProps<T, ZodNullable | ZodOptional | ZodDefault>) => {
    return <RenderField schema={schema.def.innerType} {...rest} />;
};

const UnionField = <T extends FieldValues>({
    name,
    schema,
    control,
    register,
    errors,
}: FieldRendererProps<T, ZodUnion<any>>) => {
    if (
        schema.options.length === 2 &&
        schema.options.some((opt) => opt instanceof ZodNull)
    ) {
        return (
            <RenderField
                name={name}
                schema={
                    schema.options.find(
                        (opt) => !(opt instanceof ZodNull)
                    ) as ZodType
                }
                control={control}
                register={register}
                errors={errors}
            />
        );
    }
};

const VALUE_FIELD_RENDERERS = {
    ZodString: StringField,
    ZodNumber: NumberField,
    ZodBoolean: BooleanField,
    ZodEnum: EnumField,
    ZodObject: ObjectField,
    ZodArray: ArrayField,
    ZodRecord: RecordField,
    ZodNullable: InnerField,
    ZodOptional: InnerField,
    ZodDefault: InnerField,
    ZodUnion: UnionField,
} satisfies Record<string, React.FC<FieldRendererProps<any, any>>>;

const RenderField = <T extends FieldValues>({
    name,
    schema,
    control,
    register,
    errors,
    arrayItem,
}: ZodFormFieldProps<T, ZodType>) => {
    const Renderer =
        VALUE_FIELD_RENDERERS[
            schema.constructor.name as keyof typeof VALUE_FIELD_RENDERERS
        ];

    if (!Renderer) {
        return (
            <HelperText>
                <HelperTextItem variant="error">
                    Unsupported field type: {schema.constructor.name} for field
                    "{name}"
                </HelperTextItem>
            </HelperText>
        );
    }

    return (
        <Renderer
            name={name}
            schema={schema}
            control={control}
            register={register}
            errors={errors}
        />
    );
};

export const ZodForm = <T extends FieldValues>({
    schema,
    defaultValues,
    onSubmit,
}: ZodFormProps<T>) => {
    const {
        register,
        handleSubmit,
        control,
        formState: { errors },
    } = useForm<T>({
        resolver: zodResolver(schema),
        defaultValues,
    });

    const handleFormSubmit = (data: T) => {
        if (onSubmit) onSubmit(data);
        else console.log("Form submitted:", data);
    };

    if (!(schema instanceof ZodObject)) {
        throw new Error("ZodForm only supports ZodObject schemas at the root");
    }

    return (
        <form onSubmit={handleSubmit(handleFormSubmit)}>
            {Object.entries(schema.shape).map(([key, subschema]) => (
                <RenderField
                    key={key}
                    name={key}
                    schema={subschema}
                    control={control}
                    register={register}
                    errors={errors?.[key] || ({} as any)}
                />
            ))}
            <button type="submit">Submit</button>
        </form>
    );
};

export default ZodForm;
