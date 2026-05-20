import {
    type SettingsJsonSchema,
    type Settings,
} from "../../models/api/responses/settings";
import jsonSchemaToZod from "json-schema-to-zod";
import ZodForm from "./ZodForm";
import { z } from "zod";

interface SettingsTableProps {
    schema: SettingsJsonSchema;
    settings: Settings;
    isLoading?: boolean;
    isError?: boolean;
    error?: unknown;
}

function dereferenceSchema(schema) {
    // Clone schema to avoid mutating original
    const result = structuredClone(schema);
    const defs = result.$defs || {};

    function resolveRefs(node) {
        if (Array.isArray(node)) {
            return node.map(resolveRefs);
        } else if (node && typeof node === "object") {
            if (node.$ref && node.$ref.startsWith("#/$defs/")) {
                const refName = node.$ref.replace("#/$defs/", "");
                if (!defs[refName]) {
                    throw new Error(`Missing $defs reference: ${refName}`);
                }
                return resolveRefs(structuredClone(defs[refName]));
            }

            const resolved = {};
            for (const [key, value] of Object.entries(node)) {
                resolved[key] = resolveRefs(value);
            }
            return resolved;
        }
        return node;
    }

    const deref = resolveRefs(result);
    delete deref.$defs;
    return deref;
}

const SettingsTable = ({
    schema,
    settings,
    isLoading,
    isError,
    error,
}: SettingsTableProps) => {
    // const zodSchema = eval(jsonSchemaToZod(dereferenceSchema(schema)));

    return <></>;
    // return <ZodForm schema={zodSchema} defaultValues={settings as any} />;
};

export default SettingsTable;
