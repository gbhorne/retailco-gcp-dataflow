-- Settlement summary by status
SELECT
  settlement_status,
  COUNT(*)                         AS transactions,
  ROUND(SUM(settled_amount), 2)    AS gross_volume,
  ROUND(SUM(fee_amount), 2)        AS total_fees,
  ROUND(SUM(net_amount), 2)        AS net_revenue,
  ROUND(SUM(fee_amount) /
    NULLIF(SUM(settled_amount),0)*100, 3) AS avg_fee_pct
FROM [PROJECT-ID].transactions.settlements_daily
GROUP BY settlement_status
ORDER BY gross_volume DESC
