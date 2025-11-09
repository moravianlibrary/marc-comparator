import { z } from "zod";

export const SettingsDomainSchema = z.enum(["system", "record-tools"]);
export type SettingsDomain = z.infer<typeof SettingsDomainSchema>;

export const SystemSettingsScopeSchema = z.enum(["catalog", "tasks"]);
export type SystemSettingsScope = z.infer<typeof SystemSettingsScopeSchema>;

export const RecordToolsSettingsScopeSchema = z.enum([
    "validators",
    "comparators",
    "authority-linkers",
]);
export type RecordToolsSettingsScope = z.infer<
    typeof RecordToolsSettingsScopeSchema
>;

export type SettingsScope = SystemSettingsScope | RecordToolsSettingsScope;
