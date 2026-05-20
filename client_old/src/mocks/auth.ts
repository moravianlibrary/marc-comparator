import { Response } from "miragejs";
import { PermissionSchema } from "../models/primitives/permissions";
import { faker } from "@faker-js/faker";

export function authRoutes(this: any) {
    this.post("/auth/login", (schema: any, request: any) => {
        if (faker.datatype.boolean()) {
            return {
                access_token: "mocked_jwt_token",
                token_type: "bearer",
                expires_in: 3600,
            };
        } else {
            return new Response(
                401,
                {},
                { detail: "Invalid username or password." }
            );
        }
    });

    this.post("/auth/signup", (schema: any, request: any) => {
        const attrs = JSON.parse(request.requestBody);
        if (
            attrs.email &&
            attrs.password &&
            attrs.first_name &&
            attrs.last_name
        ) {
            if (faker.datatype.boolean()) {
                return new Response(
                    400,
                    {},
                    { detail: "User registration failed" }
                );
            }
            return new Response(
                201,
                {},
                {
                    id: faker.string.uuid(),
                    email: attrs.email,
                    first_name: attrs.first_name,
                    last_name: attrs.last_name,
                    roles: [{ id: 2, name: "User" }],
                    permissions: PermissionSchema.options,
                }
            );
        } else {
            return new Response(
                400,
                {},
                { detail: "Missing required registration fields." }
            );
        }
    });

    this.get("/auth/me", (schema: any, request: any) => {
        const me = {
            id: "123e4567-e89b-12d3-a456-426614174000",
            email: "user@example.com",
            first_name: "John",
            last_name: "Doe",
            roles: [{ id: 1, name: "Admin" }],
            permissions: PermissionSchema.options,
        };
        return new Response(200, {}, me);
    });
}
