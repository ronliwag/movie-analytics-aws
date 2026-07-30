# Data directory

This folder is intentionally empty in git. Download and unzip the dataset
here before starting Week 1:

```
curl -O https://cdn.stratpoint.io/data-training/project_data.zip
unzip project_data.zip -d raw/
```

Expected layout after unzipping:

```
data/raw/movies_main.csv
data/raw/ratings.json
data/raw/movie_extended.csv
```

`data/raw/` and `data/processed/` are gitignored — never commit raw or
processed data files to this repo.
