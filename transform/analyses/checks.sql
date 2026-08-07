select count(*) from stg_submissions;

select adsh, period_end_date, filed_date,
       filed_date - period_end_date as filing_lag_days
from stg_submissions
limit 10;

select count(*) from stg_submissions where changed_date is null;

select count(*) filter (where changed is null) as raw_null,
       count(*) filter (where changed = 0) as raw_zero,
       count(*) as total
from sub;


describe sub;