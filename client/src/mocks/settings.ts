import { Response } from "miragejs";

export function settingsRoutes(this: any) {
    // GET the current Catalog settings object
    this.get("/settings/system/catalog", () => ({
        clients: [
            {
                base: "MZK01",
                oai: {
                    host: "oai.example.com",
                    endpoint: "/oai",
                    base: "MZK01",
                },
                x: null,
                z3950: null,
            },
        ],
        context: {
            ignore_unknown_tags: true,
            issue_mapping: {
                tag: "998",
                // barcode: "b",
                // issuance_type: "j",
            },
        },
    }));

    // POST updated Catalog settings
    this.post("/settings/system/catalog", (schema: any, request: any) => {
        const newSettings = JSON.parse(request.requestBody);
        console.log("Saved settings:", newSettings);
        return new Response(200, {}, newSettings);
    });
}
