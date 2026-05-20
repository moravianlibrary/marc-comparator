import { Response } from "miragejs";
import { type Task } from "../models/api/responses/task";
import { faker } from "@faker-js/faker";

export function systemRoutes(this: any) {
    // GET system info
    this.get("/system/info", (schema: any, request: any) => {
        const systemInfo = {
            system_version: "1.0.0-mock",
            system_commit: "abcdef1234567890",
            uptime_seconds: 123456,
            available_bases: ["MZK01", "MZK03"],
            enabled_authority_linkers: [
                { name: "Linker1", target_bases: ["SKC", "KNAV"] },
            ],
            enabled_comparators: ["BestComparator"],
            enabled_validators: ["ValidatorX", "ValidatorY"],
        };
        return new Response(200, {}, systemInfo);
    });
    // POST init recreate indexes task
    this.post("/system/recreate-indexes", (schema: any, request: any) => {
        const task: Task = {
            task_id: faker.string.uuid(),
            name: "Recreate Indexes",
            type: "RecreateIndexes",
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
