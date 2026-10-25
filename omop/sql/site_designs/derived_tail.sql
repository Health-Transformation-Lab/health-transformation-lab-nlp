-- Shared by all three designs: from site_rows / tooth_rows to the derived
-- person-visit measures and the 2012 CDC/AAP category (python: sites.derive, cdc_aap).
-- status: 0 present, 1 missing (other), 2 missing (periodontitis).
ip AS (
  SELECT * FROM site_rows WHERE site IN ('MB', 'DB', 'ML', 'DL')
),
tooth_ip AS (
  SELECT visit_id, tooth, MAX(cal_mm) AS cal, MAX(pd_mm) AS pd FROM ip GROUP BY visit_id, tooth
),
present AS (
  SELECT visit_id, COUNT(*) AS n_teeth_present, MAX(furcation) AS max_furcation_class,
         MAX(mobility) AS max_mobility_degree
  FROM tooth_rows WHERE status = 0 GROUP BY visit_id
),
lost AS (
  SELECT visit_id, SUM(CASE WHEN status = 2 THEN 1 ELSE 0 END) AS teeth_lost_perio FROM tooth_rows GROUP BY visit_id
),
sa AS (
  SELECT visit_id, MAX(pd_mm) AS max_probing_depth_mm, 100.0 * AVG(bop) AS bop_pct FROM site_rows GROUP BY visit_id
),
ipa AS (
  SELECT visit_id, MAX(cal_mm) AS max_cal_mm, SUM(CASE WHEN pd_mm >= 5 THEN 1 ELSE 0 END) AS n_sites_ip_pd5
  FROM ip GROUP BY visit_id
),
ta AS (
  SELECT visit_id,
         SUM(CASE WHEN cal >= 1 THEN 1 ELSE 0 END) AS n1, SUM(CASE WHEN cal >= 3 THEN 1 ELSE 0 END) AS n3,
         SUM(CASE WHEN cal >= 4 THEN 1 ELSE 0 END) AS n4, SUM(CASE WHEN cal >= 6 THEN 1 ELSE 0 END) AS n6,
         SUM(CASE WHEN pd >= 4 THEN 1 ELSE 0 END) AS p4, SUM(CASE WHEN pd >= 5 THEN 1 ELSE 0 END) AS p5
  FROM tooth_ip GROUP BY visit_id
)
SELECT p.visit_id, p.n_teeth_present, l.teeth_lost_perio, sa.max_probing_depth_mm, ipa.max_cal_mm, sa.bop_pct,
       100.0 * ta.n1 / p.n_teeth_present AS pct_teeth_ip_cal1,
       ta.n3 AS n_teeth_ip_cal3, ta.n4 AS n_teeth_ip_cal4, ta.n6 AS n_teeth_ip_cal6,
       ta.p4 AS n_teeth_ip_pd4, ta.p5 AS n_teeth_ip_pd5, ipa.n_sites_ip_pd5,
       p.max_furcation_class, p.max_mobility_degree,
       CASE WHEN ta.n6 >= 2 AND ipa.n_sites_ip_pd5 >= 1 THEN 'severe'
            WHEN ta.n4 >= 2 OR ta.p5 >= 2 THEN 'moderate'
            WHEN (ta.n3 >= 2 AND ta.p4 >= 2) OR ipa.n_sites_ip_pd5 >= 1 THEN 'mild'
            ELSE 'none' END AS cdc_aap_2012
FROM present p
JOIN lost l USING (visit_id) JOIN sa USING (visit_id) JOIN ipa USING (visit_id) JOIN ta USING (visit_id)
ORDER BY p.visit_id
