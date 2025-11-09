import { z } from "zod";
import {
    TaskSeveritySchema,
    TaskStatusSchema,
    TaskTypeSchema,
} from "../../primitives/task";

export const TaskSchema = z.object({
    task_id: z.uuidv4(),
    name: z.string(),
    type: TaskTypeSchema,
    status: TaskStatusSchema,
    outcome_severity: TaskSeveritySchema,
    created_by: z.uuidv4(),
    created_at: z.date(),
    started_at: z.date().nullable(),
    finished_at: z.date().nullable(),
});
export type Task = z.infer<typeof TaskSchema>;
