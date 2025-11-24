import json
import sys

from settings.models import SETTINGS_MODEL_DISPATCHER

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_settings_schema.py <output_dir>")
        sys.exit(1)

    output_dir = sys.argv[1]

    for scope, schema_cls in SETTINGS_MODEL_DISPATCHER.items():
        schema = schema_cls.model_json_schema()

        output_path = f"{output_dir}/{scope.value}.schema.json"

        with open(output_path, "w") as f:
            json.dump(schema, f, indent=4)
