import { Response } from "miragejs";
import { type Task } from "../models/api/responses/task";
import { faker } from "@faker-js/faker";

export function tasksRoutes(this: any) {
    // POST init deletion of tasks
    this.post("/tasks/delete", (schema: any, request: any) => {
        const task: Task = {
            task_id: faker.string.uuid(),
            name: "Delete Tasks",
            type: "DeleteTasks",
            status: "Pending",
            outcome_severity: "Info",
            created_by: faker.string.uuid(),
            created_at: new Date(),
            started_at: null,
            finished_at: null,
        };
        return new Response(200, {}, task);
    });
}
