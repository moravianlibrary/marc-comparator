import { z } from "zod";
import { type JsonSchema } from "json-schema-to-zod";

export type SettingsJsonSchema = JsonSchema;

export const SettingsSchema = z.json();
export type Settings = z.infer<typeof SettingsSchema>;
