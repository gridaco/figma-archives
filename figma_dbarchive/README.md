# dbarchive - `db.py`

Collects node info into a single sqlite db for faster analysis.

**Setup**
register this directory to your `PYTHONPATH` environment variable.

## Usage

```bash
# seeding the db from samples
python3 db.py sync ./path-to-samples-dir --db ./nodes.db

# seeding the db from samples (only root nodes)
python3 db.py sync ./path-to-samples-dir --depth 0 --db ./roots.db

# populates new db with existing one (this is usefull to populate the db on second entry when first entry only seeded with root nodes) - Also this should be re-ran when the table structure changes (for contributors)
python3 db.py populate ./roots.db --db ./nodes.db
```

## Migration / Alt table

All table columns altering is handled manually. It is not supported.
