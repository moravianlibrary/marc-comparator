import { z } from "zod";

export const TaskTypeSchema = z.enum([
    "FetchRecord",
    "FetchRecordsBatch",
    "SyncRecords",
    "ValidateRecords",
    "PairToAuthorities",
    "CompareToAuthorities",
]);
export type TaskType = z.infer<typeof TaskTypeSchema>;

export const TaskStatusSchema = z.enum([
    "Pending",
    "Started",
    "Success",
    "Failure",
    "Revoked",
]);
export type TaskStatus = z.infer<typeof TaskStatusSchema>;
