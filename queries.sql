-- =====================================================================
-- PostgreSQL queries – Game Analytics: Tennis (Sportradar)
-- =====================================================================

-- ################ 1) COMPETITIONS ################
-- 1. All competitions with category name
SELECT c.competition_id, c.competition_name, c.type, c.gender, cat.category_name
FROM competitions c
LEFT JOIN categories cat ON cat.category_id = c.category_id
ORDER BY cat.category_name, c.competition_name;

-- 2. Number of competitions in each category
SELECT cat.category_name, COUNT(*) AS total_competitions
FROM competitions c
JOIN categories cat ON cat.category_id = c.category_id
GROUP BY cat.category_name
ORDER BY total_competitions DESC;

-- 3. All competitions of type 'doubles'
SELECT competition_id, competition_name, gender, category_id
FROM competitions
WHERE type = 'doubles';

-- 4. Competitions in a specific category (e.g. ITF Men)
SELECT c.competition_id, c.competition_name, c.type, c.gender
FROM competitions c
JOIN categories cat ON cat.category_id = c.category_id
WHERE cat.category_name = 'ITF Men';

-- 5. Parent competitions and their sub-competitions
SELECT p.competition_id   AS parent_id,
       p.competition_name AS parent_name,
       ch.competition_id  AS child_id,
       ch.competition_name AS child_name
FROM competitions ch
JOIN competitions p ON p.competition_id = ch.parent_id
ORDER BY p.competition_name, ch.competition_name;

-- 6. Distribution of competition types by category
SELECT cat.category_name, c.type, COUNT(*) AS total
FROM competitions c
JOIN categories cat ON cat.category_id = c.category_id
GROUP BY cat.category_name, c.type
ORDER BY cat.category_name, total DESC;

-- 7. Top-level competitions (no parent)
SELECT competition_id, competition_name, type, gender
FROM competitions
WHERE parent_id IS NULL OR parent_id = '';

-- BONUS: competitions per level (grand_slam, atp_1000, ...)
SELECT level, type, gender, COUNT(*) AS total
FROM competitions
WHERE level IS NOT NULL
GROUP BY level, type, gender
ORDER BY total DESC;

-- ################ 2) COMPLEXES & VENUES ################
-- 1. All venues with their complex name
SELECT v.venue_id, v.venue_name, v.city_name, v.country_name, cx.complex_name
FROM venues v
JOIN complexes cx ON cx.complex_id = v.complex_id
ORDER BY cx.complex_name, v.venue_name;

-- 2. Number of venues in each complex
SELECT cx.complex_name, COUNT(v.venue_id) AS venue_count
FROM complexes cx
LEFT JOIN venues v ON v.complex_id = cx.complex_id
GROUP BY cx.complex_id, cx.complex_name
ORDER BY venue_count DESC;

-- 3. Venues in a specific country (e.g. Chile)
SELECT * FROM venues WHERE country_name = 'Chile';

-- 4. All venues and their timezones
SELECT venue_name, city_name, country_name, timezone
FROM venues
ORDER BY timezone, venue_name;

-- 5. Complexes with more than one venue
SELECT cx.complex_name, COUNT(*) AS venue_count
FROM complexes cx
JOIN venues v ON v.complex_id = cx.complex_id
GROUP BY cx.complex_id, cx.complex_name
HAVING COUNT(*) > 1
ORDER BY venue_count DESC;

-- 6. Venues grouped by country
SELECT country_name,
       COUNT(*) AS venue_count,
       STRING_AGG(venue_name, ', ' ORDER BY venue_name) AS venues
FROM venues
GROUP BY country_name
ORDER BY venue_count DESC;

-- 7. All venues for a specific complex (e.g. Nacional)
SELECT v.*
FROM venues v
JOIN complexes cx ON cx.complex_id = v.complex_id
WHERE cx.complex_name = 'Nacional';

-- ################ 3) DOUBLES COMPETITOR RANKINGS ################
-- (Uses the view v_latest_rankings = most recent week per gender.
--  Remove the view and join competitor_rankings directly to see all weeks.)

-- 1. All competitors with rank and points
SELECT c.name, c.country, r."rank", r.points
FROM competitor_rankings r
JOIN competitors c ON c.competitor_id = r.competitor_id
ORDER BY r.ranking_year DESC, r.ranking_week DESC, r."rank";

-- 2. Competitors ranked in the top 5
SELECT name, country, "rank", points, gender
FROM v_latest_rankings
WHERE "rank" <= 5
ORDER BY gender, "rank";

-- 3. Competitors with no rank movement (stable rank)
SELECT name, country, "rank", movement
FROM v_latest_rankings
WHERE movement = 0
ORDER BY "rank";

-- 4. Total points of competitors from a specific country (e.g. Croatia)
SELECT country, SUM(points) AS total_points, COUNT(*) AS competitors
FROM v_latest_rankings
WHERE country = 'Croatia'
GROUP BY country;

-- 5. Number of competitors per country
SELECT country, COUNT(*) AS competitor_count
FROM competitors
GROUP BY country
ORDER BY competitor_count DESC;

-- 6. Competitors with the highest points in the current (latest) week
SELECT name, country, "rank", points, gender
FROM v_latest_rankings v
WHERE points = (SELECT MAX(points) FROM v_latest_rankings WHERE gender = v.gender);

-- ################ BONUS (innovation) ################
-- Country-wise average points
SELECT country, COUNT(*) AS competitors, ROUND(AVG(points), 1) AS avg_points
FROM v_latest_rankings
GROUP BY country
ORDER BY avg_points DESC;

-- Biggest movers this week
SELECT name, country, "rank", movement
FROM v_latest_rankings
ORDER BY movement DESC
LIMIT 10;
