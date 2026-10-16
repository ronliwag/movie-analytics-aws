# Business Angle — Global Scouting Map

**Main business angle (unchanged):** Which country/original-language
markets are producing consistently well-rated films that haven't yet
gained wide international distribution reach — and where should we
prioritize scouting for content and co-production deals next?

**Supplementary angle:** Within those prioritized markets, which
directors and cast members have a consistently strong, audience-validated
track record across their filmography — making them the specific people
worth pursuing or investing in as we act on a market-level pick?

## Business problem

Content acquisition and international co-production decisions currently
default to the most familiar markets (the same handful of US/UK/major-
studio-adjacent countries), which risks overlooking country/original-
language markets that are producing consistently well-received films
without yet gaining international distribution reach. This project
identifies where audience-validated quality is outpacing current
international exposure, so market-scouting decisions have a data-backed
shortlist instead of relying on which regions happen to already be
familiar to the team.

Layered on top of that: once a market is shortlisted, talent decisions
(which directors/cast to pursue for deals) currently rely on reputation,
festival buzz, or agent pitches rather than a systematic view of who has
actually delivered consistently well-rated work. This adds a director/cast
track-record layer, scoped within each shortlisted market, to turn a
macro market signal into concrete people worth negotiating with.

Revenue/budget is dropped from this framing entirely — only ~19.6% of the
catalog (8,900/45,433 titles) discloses both budget and revenue, and that
disclosure itself skews toward mainstream/studio titles, i.e. toward the
same markets this analysis exists to look past. Using it as a secondary
validator would have quietly worked against the "hidden markets" thesis.
Director/cast data, by contrast, comes from the same enrichment pass with
a 98.6% director / 96.6% cast match rate (44,793 / 43,892 of 45,433
movies, verified directly against `analytics.stg_movie_extended`), making
it a more complete secondary signal than the one it replaces.

## Target audience

Head of Global Content Acquisition and the international co-production
strategy team (market-level decisions), plus acquisitions/casting
negotiators for the title- and talent-level use cases below.

## Key metrics

| Metric | Role | Basis |
|---|---|---|
| Average rating per country/original_language, weighted by total_ratings | Primary — quality signal | Ratings cover 95% of the catalog post-enrichment |
| total_ratings volume per country/language | Primary — confidence/reach filter | Prevents a single obscure high-rated title from making a market look like a hidden goldmine |
| Rating consistency (std_dev) | Primary — risk filter | Prefers markets consistently well-received over one polarizing outlier |
| Distribution gap score (rating rank vs. avg. countries/languages reached) | Primary — core scouting metric | High quality + low current international footprint = high scouting priority |
| Director/cast avg rating & consistency, computed within each shortlisted market | Secondary — talent-quality layer | Same rating fields as the market-level metrics, joined through `movie_director`/`movie_cast` (98.6%/96.6% enrichment match rate); filterable by market as a Power BI slicer |
| Filmography count + a reused "low sample" confidence flag (same pattern as `total_ratings`), not a hard minimum | Secondary — outlier/reliability signal | A hard per-market minimum risks excluding exactly the emerging/crossover talent this layer exists to surface; flagging low-sample people (rather than dropping them) lets a negotiator judge case by case, same design language already used for low-`total_ratings` titles |
| Recency/activity flag (based on `latest_release_date` in a person's filmography) | Secondary — actionability filter | Deprioritizes retired/inactive people from a "pursue" recommendation |
| Cast billing weight (`movie_cast.billing_order`, proxied from TMDB's `order` field) | Secondary — scoring input | Lead-billed cast weighted more than supporting/background credits |
| Possible-name-collision flag (`dim_person.possible_name_collision`) | Secondary — identity-risk guardrail | `person_id` is name-hashed, not TMDB-id-based (see Scope & limitations) — flags an implausible 60+ year credited career as a signal to verify identity before outreach, not just a data-quality footnote |
| Revenue (and budget) | Dropped | Only ~19.6% of the catalog discloses both, skewed toward mainstream titles — replaced by the director/cast layer above |

## Business use cases

| # | Business Use Case | Question | Who | Benefit |
|---|---|---|---|---|
| 1 | Market scouting priority | Which country/original-language markets are producing consistently well-rated films that haven't gained wide international distribution? | Head of Global Content Acquisition / co-production strategy team | Replaces gut-feel market picks with a ratings-backed shortlist of markets worth prioritizing for scouting, licensing outreach, and co-production deals |
| 2 | Title-level shortlist | Within a prioritized market, which specific titles combine strong, well-supported ratings (high avg_rating, sufficient total_ratings, low std_dev) with signs of limited international reach? | Acquisitions and licensing negotiators | Converts a macro market signal into a concrete, rankable list of titles to negotiate for |
| 3 | Talent scouting layer | Within a prioritized market, which directors/cast — filtered by recent activity and weighted toward lead billing — have a consistently well-rated filmography, with low-sample people flagged rather than hidden? | Acquisitions/casting negotiators | Turns a market-level recommendation into a concrete "pursue this person" shortlist, replacing the earlier revenue-based sanity check with a talent-quality one |

## Scope & limitations

Rankings are driven by rating quality and consistency, which cover the
near-complete catalog. Director/cast metrics are scored only within the
context of a shortlisted market (not as a standalone global leaderboard),
which is also how "international" is defined for a person — derived from
the countries/languages of the films they're linked to via
`movie_director`/`movie_cast`, since `person` has no standalone
nationality field.

`person_id` is currently deduplicated by name string, not TMDB's actual
person ID — enrichment captured director/cast as name strings only, so
two different real people sharing a name could currently merge into one
record. This is a known limitation for now; the plan is to revisit the
enrichment step to capture and preserve TMDB's actual person ID as a
follow-up, which would resolve this at the root. In the meantime,
`dim_person.possible_name_collision` flags people with an implausible
(60+ year) credited career span as a mitigation, surfaced directly on the
talent shortlist — confirmed against real data to catch exactly this
failure mode (e.g. it flags "Georges Méliès," whose linked films span
1896–2011, almost certainly a modern namesake merged with the actual
silent-film pioneer). It's a heuristic that catches long-span collisions,
not a guarantee against all of them (two different people active in the
same era, sharing a name, wouldn't trip it) — negotiators should still
verify identity independently before outreach.

Billing order (`movie_cast.billing_order`) is TMDB's own cast `order`
field, preserved via position in the enrichment pass's comma-join —
`director`/`cast` never existed in the raw source at all (both are new
columns the enrichment script adds), so there's no non-enriched cast
population where this could have drifted from the real TMDB order. It's a
positional proxy for the integer, not the integer itself (never
persisted), and it's a proxy for role prominence, not a direct performance
measure — it reflects a contractual/studio billing decision that
correlates with, but isn't identical to, screen time or impact. It's
usually capped at the top 10 credited names per movie; 80 movies show an
11th position, caused by an embedded comma inside one of the 10 real
names (e.g. a "Last, Jr." suffix) splitting into an extra token — the same
comma-ambiguity limitation already known for `production_companies`/
`genres`, not evidence of an 11th real credited person.
