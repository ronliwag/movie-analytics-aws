-- Week 1: Database Design & Implementation
-- Expand this schema to model the full dataset (movies_main.csv, ratings.json,
-- movie_extended.csv): genres, production companies, countries, ratings.
-- Add primary keys, foreign keys, and any indexes you need.

-- Example table structure you'll need to expand
CREATE TABLE movies (
    movie_id INT PRIMARY KEY,
    title VARCHAR(255),
    release_date DATE,
    budget DECIMAL(15,2),
    revenue DECIMAL(15,2)
);

-- TODO: ratings table (one-to-many or one-to-one with movies?)

-- TODO: genres table + movie_genres join table (movies have multiple genres)

-- TODO: production_companies table + movie_production_companies join table

-- TODO: countries table + movie_countries join table
