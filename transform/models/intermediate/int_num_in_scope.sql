-- The governed population: us-gaap consolidated facts.
--
-- The scope filter lives here and nowhere else. Staging is 1:1 with
-- source (F22); marts and tests inherit scope from this model rather
-- than restating it. Changing the governed population means changing
-- this WHERE clause and nothing else.
--
-- Scope axes: F19 (us-gaap, not custom = 0) and F14 (consolidated).
-- Expected 1,393,562 rows in 2025Q4.

select *

from {{ ref('stg_num') }}

where is_us_gaap
  and is_consolidated