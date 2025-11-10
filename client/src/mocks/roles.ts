import { Factory, Server } from "miragejs";
import { faker } from "@faker-js/faker";
import { type RoleResponse } from "../models/api/responses/roles";
import { PermissionSchema } from "../models/primitives/permissions";
import { Response } from "miragejs";
import { type EditRole } from "../models/api/requests/roles";

export const roleFactory = Factory.extend<RoleResponse>({
    id: () => faker.number.int({ min: 1, max: 100 }),
    name: () => faker.lorem.words(faker.number.int({ min: 1, max: 3 })),
    permissions: () =>
        faker.helpers.arrayElements(PermissionSchema.options, {
            min: 1,
            max: PermissionSchema.options.length,
        }),
    immutable: () => faker.datatype.boolean(0.3),
    protected: () => faker.datatype.boolean(0.3),
});

export function rolesSeeds(server: Server) {
    server.createList("role", 22);
}

export function rolesRoutes(this: any) {
    this.get("/access-control/roles", (schema: any, request: any) => {
        const page = Number(request.queryParams.page || 1);
        const pageSize = Number(request.queryParams.page_size || 20);

        const allRoles = schema.all("role").models as RoleResponse[];
        const total = allRoles.length;

        const start = (page - 1) * pageSize;
        const end = start + pageSize;

        const items = allRoles.slice(start, end);

        return { items, num_found: total };
    });

    this.post("/access-control/roles", (schema: any, request: any) => {
        try {
            const attrs = JSON.parse(request.requestBody) as EditRole;
            const role = schema.create("role", {
                ...attrs,
                immutable: false,
                protected: false,
            });
            return role.attrs;
        } catch (err) {
            return new Response(
                400,
                {},
                { error: "Invalid role creation payload" }
            );
        }
    });

    this.put("/access-control/roles/:id", (schema: any, request: any) => {
        const id = request.params.id;
        const role = schema.find("role", id);

        if (!role) {
            return new Response(404, {}, { error: "Role not found" });
        }

        try {
            const attrs = JSON.parse(request.requestBody) as EditRole;
            role.update(attrs);
            return role.attrs;
        } catch (err) {
            return new Response(
                400,
                {},
                { error: "Invalid role update payload" }
            );
        }
    });

    this.delete("/access-control/roles/:id", (schema: any, request: any) => {
        const id = request.params.id;
        const role = schema.find("role", id);

        if (!role) {
            return new Response(404, {}, { error: "Role not found" });
        }

        role.destroy();
        return { success: true };
    });
}
