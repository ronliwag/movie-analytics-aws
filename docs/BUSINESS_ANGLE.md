# Business Angle — Global Scouting Map

**Business angle:** Which country/original-language markets are producing
consistently well-rated films that haven't yet gained international
distribution reach — and where should we prioritize scouting for content
and co-production deals next?

## Business problem

Content acquisition and international co-production decisions currently
default to the most familiar markets (the same handful of US/UK/major-studio
-adjacent countries), which risks overlooking country/original-language
markets that are producing consistently well-received films without yet
gaining international distribution reach. This project identifies where
audience-validated quality is outpacing current international exposure, so
market-scouting decisions have a data-backed shortlist instead of relying on
which regions happen to already be familiar to the team.

## Target audience

Head of Global Content Acquisition and the international co-production
strategy team — the stakeholders deciding which country/language markets to
prioritize for new sourcing relationships and co-production deals over the
next planning cycle.

## Key metrics

| Metric | Role | Basis |
|---|---|---|
| Average rating per country / `original_language`, weighted by `total_ratings` | Primary — quality signal | Ratings cover 95% of the catalog (43,167 of 45,433 movies) post-enrichment, our most complete performance field, so this carries the main weight |
| `total_ratings` volume per country/language | Primary — confidence/reach filter | Prevents a single obscure high-rated title from making a whole market look like a hidden goldmine; also used to weight the average so small samples don't skew rankings |
| Rating consistency (`std_dev`) | Primary — risk filter | Prefers markets that are consistently well-received over ones with one polarizing outlier |
| Distribution gap score (rating rank vs. avg. number of countries/spoken languages a title from that origin reaches) | Primary — the core "scouting priority" metric | This is the actual decision output: high quality + low current international footprint = high scouting priority |
| Revenue (and budget where available) | Secondary, explicitly scoped | Only ~8,900 of 45,433 movies (19.6%) have both budget and revenue disclosed post-enrichment, and that coverage skews toward mainstream/studio titles, not the very markets this analysis is trying to surface — so financial figures are shown only as supporting context where they exist, never as a qualifying requirement for a market to rank |

## Scope & limitations

Rankings are driven by rating quality and consistency, which cover the
near-complete catalog; revenue is shown as a secondary, opportunistic signal
only for the minority of titles that disclose it, and its absence for a
given market should not be read as poor financial performance — it's a
known gap in TMDB's crowd-sourced financial coverage, concentrated on
non-mainstream titles.

## Grounding the "why" — 3 business use cases (Global Scouting Map angle)

| # | Business Use Case | Question | Who | Benefit |
|---|---|---|---|---|
| 1 | Market scouting priority | Which country / original-language markets are producing consistently well-rated films that haven't gained wide international distribution? | Head of Global Content Acquisition / co-production strategy team | Replaces gut-feel market picks with a ratings-backed shortlist of markets worth prioritizing for scouting trips, licensing outreach, and co-production deals |
| 2 | Title-level shortlist | Within a prioritized market, which specific titles combine strong, well-supported ratings (high avg_rating, sufficient total_ratings, low std_dev) with signs of limited international reach? | Acquisitions and licensing negotiators | Converts a macro market signal into a concrete, rankable list of titles to actually negotiate for, instead of an unfiltered catalog |
| 3 | Financial sanity check | For the subset of shortlisted titles/markets that do have disclosed budget and revenue (~19.6% of the catalog, 8,900 of 45,433 movies), does financial performance support or contradict the ratings-based recommendation? | Finance / greenlight committee reviewing the acquisition slate | Adds a secondary, explicitly-scoped risk check before committing spend, without letting the large financial-data gap block the primary ratings-driven analysis |
