import { createServer, Model, Server } from "miragejs";
import {
    catalogRecordFactory,
    catalogRecordRoutes,
    catalogRecordSeeds,
} from "./catalog_record";
import type { CatalogRecord } from "../models/api/responses/catalog_record";

export function makeServer() {
    return createServer({
        models: {
            catalogRecord: Model.extend<Partial<CatalogRecord>>({}),
        },
        factories: {
            catalogRecord: catalogRecordFactory,
        },
        seeds: (server: Server) => {
            catalogRecordSeeds(server);
        },
        routes() {
            this.passthrough("/locales/**");
            this.namespace = "api";
            catalogRecordRoutes.call(this);
        },
    });
}
