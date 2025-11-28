import { z } from "zod";
import {
    TaskSeveritySchema,
    TaskStatusSchema,
    TaskTypeSchema,
} from "../../primitives/task";
import { createEsHitSchema, createEsResponseSchema } from "./es";

export const TaskSchema = z.object({
    name: z.string(),
    type: TaskTypeSchema,
    status: TaskStatusSchema,
    severity: TaskSeveritySchema,
    created_by: z.uuidv4(),
    created_at: z.coerce.date(),
    started_at: z.coerce.date().nullable(),
    finished_at: z.coerce.date().nullable(),
    traceback_lines: z.number().nullable(),
});
export type Task = z.infer<typeof TaskSchema>;

export const EsHitTaskSchema = createEsHitSchema(TaskSchema);
export type EsHitTask = z.infer<typeof EsHitTaskSchema>;

export const SearchTasksResponseSchema = createEsResponseSchema(
    TaskSchema.partial()
);
export type SearchTasksResponse = z.infer<typeof SearchTasksResponseSchema>;

export type TaskTraceback = string[];

export const TracebackLinesRequestParamsSchema = z.object({
    from: z.number().min(0).nullable().default(null),
    to: z.number().min(0).nullable().default(null),
});
export type TracebackLinesRequestParams = z.infer<
    typeof TracebackLinesRequestParamsSchema
>;
