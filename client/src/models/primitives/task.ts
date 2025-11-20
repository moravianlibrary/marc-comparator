import { z } from "zod";

export const TaskTypeSchema = z.enum([
    "FetchRecord",
    "FetchBatchOfRecords",
    "SyncRecords",
    "LinkRecordsToAuthorities",
    "CompareRecords",
    "ValidateRecords",
    "SetRecordsHiddenState",
    "ReindexRecords",
    "DeleteTasks",
    "RecreateIndexes",
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

export const TaskSeveritySchema = z.enum([
    "Info",
    "Warning",
    "Error",
    "Critical",
]);
export type TaskSeverity = z.infer<typeof TaskSeveritySchema>;
