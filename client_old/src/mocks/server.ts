import { createServer, Model, Server } from "miragejs";
import {
    catalogRecordFactory,
    catalogRecordRoutes,
    catalogRecordSeeds,
    marcRecordFactory,
} from "./catalog_record";
import type { CatalogRecord } from "../models/api/responses/catalog_record";
import { settingsRoutes } from "./settings";
import { taskFactory, taskSeeds, tasksRoutes } from "./tasks";
import { systemRoutes } from "./system";
import { roleFactory, rolesRoutes, rolesSeeds } from "./roles";
import { type RoleResponse } from "../models/api/responses/roles";
import { type User } from "../models/api/responses/users";
import { userFactory, usersRoutes, usersSeeds } from "./users";
import type { MarcRecord } from "../models/api/responses/marc_record";
import type { Task } from "../models/api/responses/task";
import { authRoutes } from "./auth";

export function makeServer() {
    return createServer({
        models: {
            catalogRecord: Model.extend<Partial<CatalogRecord>>({}),
            role: Model.extend<Partial<RoleResponse>>({}),
            user: Model.extend<Partial<User>>({}),
            marcRecord: Model.extend<Partial<MarcRecord>>({}),
            task: Model.extend<Partial<Task>>({}),
        },
        factories: {
            catalogRecord: catalogRecordFactory,
            role: roleFactory,
            user: userFactory,
            marcRecord: marcRecordFactory,
            task: taskFactory,
        },
        seeds: (server: Server) => {
            catalogRecordSeeds(server);
            rolesSeeds(server);
            usersSeeds(server);
            taskSeeds(server);
        },
        routes() {
            this.passthrough("/locales/**");
            this.passthrough("/schemas/**");
            this.namespace = "api";
            catalogRecordRoutes.call(this);
            rolesRoutes.call(this);
            settingsRoutes.call(this);
            systemRoutes.call(this);
            tasksRoutes.call(this);
            usersRoutes.call(this);
            authRoutes.call(this);
        },
    });
}
