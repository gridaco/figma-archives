import click
import jsonlines


@click.group()
def cli():
    pass


@cli.command('validate')
@click.argument('path', type=click.Path(exists=True))
def validate(path):
    with jsonlines.open(path) as reader:
        for index, item in enumerate(reader, start=1):
            try:
                reader.read(item)
            except jsonlines.jsonlines.InvalidLineError as e:
                print(f"Invalid json on line {index}: {e}")
            except Exception as e:
                print(f"Exception on line {index}: {e}")


if __name__ == '__main__':
    cli()
