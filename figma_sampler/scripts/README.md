## Utility scripts

### `reduce.py`

Reduces the input directories item to `--to` amount. This removes the item from the input dir, so be careful.

This is useful to resize the samples to a smaller size. if you sampled with marginal amount of items.

```bash
python3 reduce.py path/to/input/dir
  \ --input=''
  \ --to=1000
```

### `resample.py`

Resample a random sample of `--max` amount from the input directory.
and copies them to the `--out` directory.

This is useful to re-sample with existing samples with smaller size.

```bash
python3 resample.py path/to/input/dir
  \ --out='path-to-output-dir'
  \ --max=1000


# for example, sampling for 5k.min
python3 resample.py /Volumes/WDB2TB/Data/figma-archives\
  --out='/Volumes/WDB2TB/Data/figma-samples-5k.min'\
  --depth=1\
  --max=5000
```
