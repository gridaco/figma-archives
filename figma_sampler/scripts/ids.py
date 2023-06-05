###
# python ids.py <input.json> <output.txt> --key <key>
###

import click
import json


@click.command()
@click.argument('input', type=click.File('r'))
@click.argument('output', type=click.File('w'))
@click.option('--key', type=str, default='id')
def main(input, output, key):
    # read the input file (json)
    data = json.load(input)

    # extract ids with key
    ids = [obj[key] for obj in data]

    # write the ids to output file (txt)
    output.write('\n'.join(ids))

    # log result
    click.echo(f"📝 {len(ids)} ids written to {output.name}")


if __name__ == '__main__':
    main()
