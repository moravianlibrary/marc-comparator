import { Factory, Server } from "miragejs";
import { faker } from "@faker-js/faker";
import { type User } from "../models/api/responses/users";
import { Response } from "miragejs";

export const userFactory = Factory.extend<User>({
    id: () => faker.string.uuid(),
    email: () => faker.internet.email(),
    first_name: () => faker.person.firstName(),
    last_name: () => faker.person.lastName(),
    roles: () =>
        faker.helpers.arrayElements(
            [
                { id: 1, name: "admin" },
                { id: 2, name: "editor" },
                { id: 3, name: "viewer" },
            ],
            { min: 1, max: 3 }
        ),
});

export function usersSeeds(server: Server) {
    server.createList("user", 22);
}

export function usersRoutes(this: any) {
    this.get("/access-control/users", (schema: any, request: any) => {
        const page = Number(request.queryParams.page || 1);
        const pageSize = Number(request.queryParams.page_size || 20);
        const searchTerm = request.queryParams.email || null;

        const allusers = searchTerm
            ? schema
                  .all("user")
                  .models.filter((user: User) =>
                      user.email.includes(searchTerm)
                  )
            : schema.all("user").models;

        const total = allusers.length;

        const start = (page - 1) * pageSize;
        const end = start + pageSize;

        const items = allusers.slice(start, end);

        return { items, num_found: total };
    });

    this.patch(
        "/access-control/users/:user_id/assign-role/:role_id",
        (schema: any, request: any) => {
            const { user_id } = request.params;
            const user = schema.find("user", user_id);
            if (!user) {
                return new Response(404, {}, { error: "User not found" });
            }
            return user.attrs;
        }
    );

    this.patch(
        "/access-control/users/:user_id/unassign-role/:role_id",
        (schema: any, request: any) => {
            const { user_id } = request.params;
            const user = schema.find("user", user_id);
            if (!user) {
                return new Response(404, {}, { error: "User not found" });
            }
            return user.attrs;
        }
    );
}
