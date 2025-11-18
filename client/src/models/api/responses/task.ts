import { z } from "zod";
import {
    TaskSeveritySchema,
    TaskStatusSchema,
    TaskTypeSchema,
} from "../../primitives/task";
import { createEsResponseSchema } from "./es";

export const TaskSchema = z.object({
    task_id: z.uuidv4(),
    name: z.string(),
    type: TaskTypeSchema,
    status: TaskStatusSchema,
    outcome_severity: TaskSeveritySchema,
    created_by: z.uuidv4(),
    created_at: z.coerce.date(),
    started_at: z.coerce.date().nullable(),
    finished_at: z.coerce.date().nullable(),
});
export type Task = z.infer<typeof TaskSchema>;

export const SearchTasksResponseSchema = createEsResponseSchema(
    TaskSchema.partial()
);
export type SearchTasksResponse = z.infer<typeof SearchTasksResponseSchema>;
