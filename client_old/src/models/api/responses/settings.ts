import { z } from "zod";
import { type JsonSchema } from "json-schema-to-zod";

export type SettingsJsonSchema = JsonSchema;

export const SettingsSchema = z.record(z.string(), z.any());
export type Settings = z.infer<typeof SettingsSchema>;
