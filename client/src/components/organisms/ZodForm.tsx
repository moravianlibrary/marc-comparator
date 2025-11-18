import {
    useForm,
    useFieldArray,
    type Control,
    type FieldValues,
    type UseFormRegister,
    type FieldErrors,
    type DefaultValues,
    Controller,
    type UseFieldArrayRemove,
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
} from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import {
    Button,
    FormGroup,
    HelperText,
    HelperTextItem,
    MenuToggle,
    type MenuToggleElement,
    Select,
    SelectOption,
    Form,
    Switch,
    TextInput,
    FormFieldGroupExpandable,
    FormFieldGroupHeader,
} from "@patternfly/react-core";
import { useState } from "react";
import React from "react";

export interface ZodFormProps<T extends FieldValues> {
    schema: ZodType<T, any, any>;
    defaultValues?: DefaultValues<T>;
    onSubmit?: (data: T) => void;
}

interface AnyFormFieldProps<T extends FieldValues, S extends ZodType> {
    name: string;
    schema: S;
    control: Control<T>;
    register: UseFormRegister<T>;
    errors: FieldErrors<T>;
    isRequired?: boolean;
    remove?: UseFieldArrayRemove;
}

const FieldError = <T extends FieldValues>(props: {
    errors?: FieldErrors<T>;
}) =>
    props.errors?.message ? (
        <HelperText>
            <HelperTextItem variant="error">
                {String(props.errors.message)}
            </HelperTextItem>
        </HelperText>
    ) : null;

const FieldContainer = <T extends FieldValues, S extends ZodType>({
    name,
    schema,
    isRequired,
    children,
}: AnyFormFieldProps<T, S>) => (
    <FormGroup
        label={name}
        fieldId={name}
        helperText={schema.description}
        isRequired={isRequired}
    >
        {children}
    </FormGroup>
);

const StringField = <T extends FieldValues>(
    props: AnyFormFieldProps<T, ZodString>
) => (
    <FieldContainer {...props}>
        <Controller
            name={props.name as any}
            control={props.control}
            render={({ field }) => (
                <TextInput
                    {...field}
                    type="text"
                    validated={props.errors?.message ? "error" : "success"}
                />
            )}
        />
        <FieldError {...props} />
    </FieldContainer>
);

const NumberField = <T extends FieldValues>(
    props: AnyFormFieldProps<T, ZodNumber>
) => (
    <FieldContainer {...props}>
        <Controller
            {...props}
            render={({ field }) => (
                <TextInput
                    {...field}
                    type="number"
                    validated={props.errors?.message ? "error" : "success"}
                />
            )}
        />
        <FieldError {...props} />
    </FieldContainer>
);

const BooleanField = <T extends FieldValues>(
    props: AnyFormFieldProps<T, ZodBoolean>
) => (
    <FieldContainer {...props}>
        <Controller
            {...props}
            render={({ field }) => (
                <Switch
                    {...field}
                    isChecked={field.value}
                    onChange={field.onChange}
                    label={props.name}
                />
            )}
        />
        <FieldError {...props} />
    </FieldContainer>
);

const EnumField = <T extends FieldValues>(
    props: AnyFormFieldProps<T, ZodEnum<any>>
) => {
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
        <FieldContainer {...props}>
            <Controller
                {...props}
                render={({ field }) => (
                    <Select
                        {...field}
                        isOpen={isOpen}
                        onOpenChange={setIsOpen}
                        toggle={toggle}
                    >
                        {props.schema.options.map((opt) => (
                            <SelectOption key={opt} value={opt}>
                                {opt}
                            </SelectOption>
                        ))}
                    </Select>
                )}
            />
            <FieldError {...props} />
        </FieldContainer>
    );
};

// const ObjectField = <T extends FieldValues>({
//     name,
//     schema,
//     control,
//     register,
//     errors,
// }: FieldRendererProps<T, ZodObject<any>>) => (
//     <SectionContainer name={name}>
//         <DescriptionList>
//             {Object.entries(schema.shape).map(([key, subschema]) => (
//                 <RenderField
//                     key={key}
//                     name={`${name}.${key}`}
//                     schema={subschema}
//                     control={control}
//                     register={register}
//                     errors={errors?.[key] || ({} as any)}
//                 />
//             ))}
//         </DescriptionList>
//     </SectionContainer>
// );

// const RecordField = <T extends FieldValues>({
//     name,
//     schema,
//     control,
//     register,
//     errors,
// }: FieldRendererProps<T, ZodRecord<any, any>>) => {
//     const { fields, append, remove } = useFieldArray({
//         control,
//         name: name as any,
//     });

//     const keyType = schema.def.valueType ? schema.def.keyType : z.string();
//     const valueType = schema.def.valueType ?? schema.def.keyType;

//     if (
//         !(
//             keyType instanceof ZodString ||
//             keyType instanceof ZodNumber ||
//             keyType instanceof ZodEnum
//         )
//     ) {
//         return (
//             <HelperText>
//                 <HelperTextItem variant="error">
//                     Unsupported record key type: {keyType.constructor.name} for
//                     field "{name}"
//                 </HelperTextItem>
//             </HelperText>
//         );
//     }

//     return (
//         <FieldContainer name={name} schema={schema}>
//             {fields.map((field, index) => (
//                 <SectionContainer key={field.id} name={`Item ${index + 1}`}>
//                     <RenderField
//                         key={field.id}
//                         name={`${name}[${index}]`}
//                         schema={valueType as ZodType<any>}
//                         control={control}
//                         register={register}
//                         errors={errors?.[index] || ({} as any)}
//                     />
//                 </SectionContainer>
//             ))}
//             <Label
//                 color="blue"
//                 onClick={() =>
//                     append(
//                         (valueType instanceof ZodObject
//                             ? {}
//                             : valueType instanceof ZodArray
//                             ? []
//                             : "") as any
//                     )
//                 }
//             >
//                 Add item
//             </Label>
//         </FieldContainer>
//     );
// };

// const InnerField = <T extends FieldValues>({
//     schema,
//     ...rest
// }: ZodFormFieldProps<T, ZodNullable | ZodOptional | ZodDefault>) => {
//     return <RenderField schema={schema.def.innerType} {...rest} />;
// };

// const UnionField = <T extends FieldValues>({
//     name,
//     schema,
//     control,
//     register,
//     errors,
// }: FieldRendererProps<T, ZodUnion<any>>) => {
//     if (
//         schema.options.length === 2 &&
//         schema.options.some((opt) => opt instanceof ZodNull)
//     ) {
//         return (
//             <RenderField
//                 name={name}
//                 schema={
//                     schema.options.find(
//                         (opt) => !(opt instanceof ZodNull)
//                     ) as ZodType
//                 }
//                 control={control}
//                 register={register}
//                 errors={errors}
//             />
//         );
//     }
// };
function getNewItemValue(schema: ZodType): any {
    if (schema instanceof ZodObject) {
        const shape = schema.shape;
        const obj: any = {};
        for (const key in shape) {
            obj[key] = getNewItemValue(shape[key]);
        }
        return obj;
    } else if (schema instanceof ZodArray) {
        return [];
    } else if (schema instanceof ZodString) {
        return "";
    } else if (schema instanceof ZodNumber) {
        return 0;
    } else if (schema instanceof ZodBoolean) {
        return false;
    } else if (schema instanceof ZodEnum) {
        return schema.options[0];
    } else if (schema instanceof ZodOptional || schema instanceof ZodNullable) {
        return null;
    }
    return null;
}

const ObjectFormField = <T extends FieldValues>(
    props: AnyFormFieldProps<T, ZodObject<any>>
) => {
    return (
        <FormFieldGroupExpandable>
            {Object.entries(props.schema.shape).map(([key, subschema]) => (
                <RenderField {...props} />
            ))}
        </FormFieldGroupExpandable>
    );
};

const ArrayFormField = <T extends FieldValues>(
    props: AnyFormFieldProps<T, ZodArray<any>>
) => {
    const { fields, append, remove } = useFieldArray({
        name: props.name,
        control: props.control,
    });

    return (
        <FormFieldGroupExpandable
            header={
                <FormFieldGroupHeader
                    titleText={{ text: props.name, id: `${props.name}-header` }}
                    actions={
                        <>
                            <Button variant="link" isDanger>
                                Delete all
                            </Button>
                            <Button
                                variant="secondary"
                                onClick={() =>
                                    append(
                                        getNewItemValue(props.schema.element)
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
            {fields.map((field, index) => (
                <RenderField
                    {...props}
                    name={`${props.name}[${index}]`}
                    schema={props.schema.element as ZodType<any>}
                    errors={props.errors?.[index] || ({} as any)}
                    remove={remove}
                />
            ))}
        </FormFieldGroupExpandable>
    );
};

const VALUE_FIELD_RENDERERS = {
    ZodString: StringField,
    ZodNumber: NumberField,
    ZodBoolean: BooleanField,
    ZodEnum: EnumField,
    ZodObject: ObjectFormField,
    ZodArray: ArrayFormField,
    // ZodRecord: RecordField,
    // ZodNullable: InnerField,
    // ZodOptional: InnerField,
    // ZodDefault: InnerField,
    // ZodUnion: UnionField,
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

// const ArrayFormField = <T extends FieldValues>({
//     name,
//     schema,
//     control,
//     register,
//     errors,
// }: ZodFormFieldProps<T, ZodArray<any>>) => {
//     const { fields, append, remove } = useFieldArray({
//         name,
//         control,
//     });
// };

const RootObjectFormField = <T extends FieldValues>({
    schema,
    control,
    register,
    errors,
}: ZodFormFieldProps<T, ZodObject<any>>) => {
    return (
        <FormGroup>
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
        </FormGroup>
    );
};

const AnyFormField = <T extends FieldValues>({
    name,
    schema,
    control,
    register,
    errors,
}: ZodFormFieldProps<T, ZodType>) => {
    if (schema instanceof ZodObject) {
        return (
            <ObjectFormField
                name={name}
                schema={schema}
                control={control}
                register={register}
                errors={errors}
            />
        );
    }
    if (schema instanceof ZodArray) {
        return (
            <ArrayFormField
                name={name}
                schema={schema}
                control={control}
                register={register}
                errors={errors}
            />
        );
    }
    if (schema instanceof ZodOptional || schema instanceof ZodNullable) {
        return (
            <AnyFormField
                name={name}
                schema={schema.def.innerType}
                control={control}
                register={register}
                errors={errors}
            />
        );
    }
    console.log("Unsupported AnyFormField schema:", schema);
};
export const ZodForm = <T extends FieldValues>({
    schema,
    defaultValues,
    onSubmit,
}: ZodFormProps<T>) => {
    const {
        control,
        register,
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
        <Form onSubmit={(data) => handleFormSubmit(data as T)}>
            <RootObjectFormField
                name=""
                schema={schema}
                control={control}
                register={register}
                errors={errors}
            />
        </Form>
    );
};

export default ZodForm;
