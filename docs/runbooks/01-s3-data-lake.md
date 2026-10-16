# Runbook: S3 data lake (Phase 1)

How the S3 bucket was created and populated with the project's raw, enriched
and MovieLens data. Run all commands from the repo root in WSL.

## Prerequisites

| Requirement | Check |
|---|---|
| AWS CLI v2, profile `movie-pipeline` (least-privilege: S3 `ron-movie-lake-*`) | `aws sts get-caller-identity` → Arn ends in `user/movie-pipeline` |
| Python venv with `requirements.txt` | `source venv/bin/activate` |
| TMDB API key in `.env` (`TMDB_API_KEY=`) | Needed for enrichment only |

```bash
export AWS_PROFILE=movie-pipeline         # run the pipeline as the least-privilege user
export BUCKET=ron-movie-lake-capstone     # add both lines to ~/.bashrc to keep them
```

## 1. Build the local data

`data/` is gitignored, so on a new machine it must be rebuilt first.

```bash
./scripts/download_data.sh                              # raw dataset → data/raw/
python -m scripts.enrichment.fill_missing               # TMDB gap-filling → data/enriched/ (~40 min, cached, resumable)
python -m scripts.enrichment.movielens_ratings          # needs ml-32m in data/external/movielens/
python -m scripts.enrichment.validate_records           # corrects values against TMDB (reuses cache)
python -m scripts.pandas.clean_data                     # → data/processed/
```

Expected: 45,433 movies and 43,167 ratings (see `scripts/enrichment/RESULTS.md`).

## 2. Create the bucket (console, admin user)

The pipeline user can't create buckets on purpose; it only has data permissions.
In the S3 console, region **ap-southeast-1**:

- Name: `ron-movie-lake-capstone` (global, lowercase; must match `ron-movie-lake-*` in the IAM policy)
- Block all public access: **on**
- Bucket Versioning: **enabled**, so overwritten or deleted files can be recovered
- Default encryption: SSE-S3

Check the pipeline user can reach it:

```bash
aws s3 ls s3://$BUCKET/          # empty output, no error = OK
```

## 3. Upload the data

S3 has no real folders. Prefixes such as `raw/` appear when the first object is uploaded.

```bash
# Raw source files
aws s3 sync data/raw/ s3://$BUCKET/raw/project_data/

# Enriched files, without the 45K-file TMDB cache
aws s3 sync data/enriched/ s3://$BUCKET/enriched/ --exclude "tmdb_cache/*"

# TMDB cache as ONE archive: 1 request instead of ~45K, 873 MB → ~159 MB
tar czf ~/tmdb_cache.tar.gz -C data/enriched tmdb_cache
aws s3 cp ~/tmdb_cache.tar.gz s3://$BUCKET/enriched/tmdb_cache.tar.gz

# MovieLens: gzipped (~900 MB → ~210 MB), one prefix per file so each can become an Athena table
gzip -c data/external/movielens/ratings.csv > /tmp/ratings.csv.gz
gzip -c data/external/movielens/links.csv   > /tmp/links.csv.gz
aws s3 cp /tmp/ratings.csv.gz s3://$BUCKET/raw/movielens/ratings/ratings.csv.gz
aws s3 cp /tmp/links.csv.gz   s3://$BUCKET/raw/movielens/links/links.csv.gz
rm /tmp/ratings.csv.gz /tmp/links.csv.gz
```

`data/processed/` is uploaded in Phase 2, once it's written as Parquet.

## 4. Verify

```bash
aws s3 ls s3://$BUCKET/ --recursive --summarize --human-readable
```

Expected: 11 objects, about 407 MiB:

```
raw/project_data/        movies_main.csv, movie_extended.csv, ratings.json
raw/movielens/ratings/   ratings.csv.gz
raw/movielens/links/     links.csv.gz
enriched/                movies_main.csv, movie_extended.csv, ratings.json,
                         validation_report.csv, ratings_validation_report.csv,
                         tmdb_cache.tar.gz
```

## 5. Versioning check (optional)

```bash
echo v1 > /tmp/t.txt && aws s3 cp /tmp/t.txt s3://$BUCKET/scratch/t.txt
echo v2 > /tmp/t.txt && aws s3 cp /tmp/t.txt s3://$BUCKET/scratch/t.txt
```

In the console, open `scratch/t.txt` → **Versions** and download the older version (`v1`).
To remove the test completely, turn on **Show versions** and delete both versions.
A plain delete only adds a delete marker.

## Restore the TMDB cache on another machine

```bash
aws s3 cp s3://$BUCKET/enriched/tmdb_cache.tar.gz ~/
tar xzf ~/tmdb_cache.tar.gz -C data/enriched     # enrichment re-runs then skip the API
```

## Troubleshooting

| Error | Cause / fix |
|---|---|
| `NoCredentials` | No active profile: `export AWS_PROFILE=movie-pipeline` |
| `AccessDenied` on the bucket | Bucket name doesn't match `ron-movie-lake-*`, or you're signed in as the wrong user (`aws sts get-caller-identity`) |
| Upload works but Arn shows `ron-admin` | `aws login` set the `default` profile to admin; set `AWS_PROFILE=movie-pipeline` |

## Cost

About 407 MiB of storage plus a few dozen requests ≈ $0.01/month, or free under the Free Tier.
