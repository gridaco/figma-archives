###
### converts map.json to csv
### python csvmap.py <map.json> <map.csv>
###

import click
import json
import csv

@click.command()
@click.argument('input', type=click.File('r'))
@click.argument('output', type=click.File('w'))
def main(input, output):
    data = json.load(input)

    # write csv
    writer = csv.writer(output)
    for key, value in data.items():
        k = key.split('/')[-1]
        v = value.split('/')[-1]
        writer.writerow([k, v])

if __name__ == '__main__':
    main()