import { Factory, Response, Server } from "miragejs";
import { type Task } from "../models/api/responses/task";
import { faker } from "@faker-js/faker";
import { buildSearchResponse } from "./es_factories";
import {
    TaskSeveritySchema,
    TaskStatusSchema,
    TaskTypeSchema,
} from "../models/primitives/task";

export const taskFactory = Factory.extend<Task>({
    task_id: () => faker.string.uuid(),
    name: () => `Task ${faker.number.int({ min: 1, max: 1000 })}`,
    type: () => faker.helpers.arrayElement(TaskTypeSchema.options),
    status: () => faker.helpers.arrayElement(TaskStatusSchema.options),
    severity: () => faker.helpers.arrayElement(TaskSeveritySchema.options),
    created_by: () => faker.string.uuid(),
    created_at: () => faker.date.past(),
    started_at: () => (faker.datatype.boolean() ? faker.date.recent() : null),
    finished_at: () => (faker.datatype.boolean() ? faker.date.recent() : null),
    traceback_lines: () =>
        faker.datatype.boolean()
            ? faker.number.int({ min: 5, max: 2000 })
            : null,
});

export function taskSeeds(server: Server) {
    server.createList("task", 42);
}

export function tasksRoutes(this: any) {
    this.post("/tasks/search", (schema: any, request: any) =>
        buildSearchResponse(
            schema,
            request,
            "task",
            (task: Task) => task.task_id
        )
    );

    this.get("/tasks/:id/traceback", (schema: any, request: any) => {
        const { id } = request.params;
        const task = schema.tasks.findBy({ task_id: id }) as Task;
        if (!task) {
            return new Response(404, {}, { error: "Task not found" });
        }

        const lines: string[] = [];
        const totalLines = task.traceback_lines || 100;
        for (let i = 0; i < totalLines; i++) {
            lines.push(`Traceback line ${i + 1} for task ${id}`);
        }
        return new Response(200, {}, lines);
    });

    // POST init deletion of tasks
    this.post("/tasks/delete", (schema: any, request: any) => {
        const task: Task = {
            task_id: faker.string.uuid(),
            name: "Delete Tasks",
            type: "DeleteTasks",
            status: "Pending",
            severity: "Info",
            created_by: faker.string.uuid(),
            created_at: new Date(),
            started_at: null,
            finished_at: null,
        };
        return new Response(200, {}, task);
    });
}
