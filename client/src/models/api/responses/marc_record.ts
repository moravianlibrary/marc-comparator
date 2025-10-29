import { z } from "zod";

export const TagSchema = z.string().regex(/^\d{3}$/);
export type Tag = z.infer<typeof TagSchema>;

export const IndicatorSchema = z.string().regex(/^[\s\d]$/);
export type Indicator = z.infer<typeof IndicatorSchema>;

export const CodeSchema = z.string().regex(/^[a-z0-9]$/);
export type Code = z.infer<typeof CodeSchema>;

export const FixedFieldsSchema = z.record(TagSchema, z.string());
export type FixedFields = z.infer<typeof FixedFieldsSchema>;

export const SubfieldsSchema = z.record(CodeSchema, z.array(z.string()));
export type Subfields = z.infer<typeof SubfieldsSchema>;

export const VariableFieldSchema = z.object({
    ind1: IndicatorSchema,
    ind2: IndicatorSchema,
    subfields: SubfieldsSchema,
});
export type VariableField = z.infer<typeof VariableFieldSchema>;

export const VariableFieldsSchema = z.record(
    TagSchema,
    z.array(VariableFieldSchema)
);
export type VariableFields = z.infer<typeof VariableFieldsSchema>;

export const MarcRecordSchema = z.object({
    leader: z.string(),
    fixed_fields: FixedFieldsSchema,
    variable_fields: VariableFieldsSchema,
});
export type MarcRecord = z.infer<typeof MarcRecordSchema>;
