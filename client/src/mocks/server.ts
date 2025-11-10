import { createServer, Model, Server } from "miragejs";
import {
    catalogRecordFactory,
    catalogRecordRoutes,
    catalogRecordSeeds,
} from "./catalog_record";
import type { CatalogRecord } from "../models/api/responses/catalog_record";
import { settingsRoutes } from "./settings";
import { tasksRoutes } from "./tasks";
import { systemRoutes } from "./system";
import { roleFactory, rolesRoutes, rolesSeeds } from "./roles";
import { type RoleResponse } from "../models/api/responses/roles";
import { type User } from "../models/api/responses/users";
import { userFactory, usersRoutes, usersSeeds } from "./users";

export function makeServer() {
    return createServer({
        models: {
            catalogRecord: Model.extend<Partial<CatalogRecord>>({}),
            role: Model.extend<Partial<RoleResponse>>({}),
            user: Model.extend<Partial<User>>({}),
        },
        factories: {
            catalogRecord: catalogRecordFactory,
            role: roleFactory,
            user: userFactory,
        },
        seeds: (server: Server) => {
            catalogRecordSeeds(server);
            rolesSeeds(server);
            usersSeeds(server);
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
        },
    });
}
