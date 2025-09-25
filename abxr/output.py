import json
import yaml

from abxr.formats import DataOutputFormats

def print_formatted(format, data):
    if format == DataOutputFormats.JSON.value:
        print(json.dumps(data))
    elif format == DataOutputFormats.YAML.value:
        print(yaml.dump(data))
    else:
        print("Invalid output format.")