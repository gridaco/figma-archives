import click
import json


@click.command()
@click.argument('input', type=click.Path(exists=True, dir_okay=False))
@click.argument('output', type=click.Path(exists=False, dir_okay=False))
def main(input, output):
    with open(input) as input:
        data = json.load(input)

    with open(output, 'w') as outfile:
        for entry in data:
            json.dump(entry, outfile)
            outfile.write('\n')

    click.echo(f'Wrote {len(data)} entries to {output}')


if __name__ == '__main__':
    main()
