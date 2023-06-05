###
# Extracts values k:v formatted csv, stores in a line separated txt
# python csvmap_values.py <map.csv> <values.txt>
###


import click
import csv


@click.command()
@click.argument('input', type=click.File('r'))
@click.argument('output', type=click.File('w'))
def main(input, output):
    data = csv.reader(input)

    # values from csv
    values = [v for k, v in data]

    # write out to txt
    output.write('\n'.join(values))

    # log result
    print(f"📦 {len(values)} values written to '{output.name}'")


if __name__ == '__main__':
    main()
