import json
import click
from tqdm import tqdm


@click.command()
@click.argument('meta_file', type=click.Path(exists=True))
@click.argument('map_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
def process_files(meta_file, map_file, output_file):
    # Read map file
    with open(map_file, 'r') as f:
        map_data = json.load(f)

    # Prepare the output data structure
    output_data = {}

    # Process meta file
    with open(meta_file, 'r') as f:
        for line in tqdm(f, desc='Processing meta data'):
            meta_data = json.loads(line)

            id_ = meta_data['id']
            version_id = meta_data['version_id']
            version = meta_data['version']

            # Find the corresponding map entry
            map_key = f'https://www.figma.com/community/file/{id_}'
            map_value = map_data.get(map_key)

            if map_value:
                # Construct the output structure
                output_data[id_] = {
                    'tags': {
                        'mirror': version_id,
                        'latest': version_id,
                        version: version_id
                    },
                    'versions': {
                        version_id: map_value.split('/')[-1]
                    }
                }

    # Write output file
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f'Data successfully written to {output_file}.')


if __name__ == '__main__':
    process_files()
