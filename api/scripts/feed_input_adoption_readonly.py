"""Feed input adoption audit — READ-ONLY aggregates (docs/feed/FEED_INPUT_ADOPTION_AUDIT_20260922.md).

용법 (프로덕션은 api 컨테이너 안에서, DATABASE_URL 을 그대로 사용):
    ssh <host> 'sudo docker exec -i pigos-api python -' < api/scripts/feed_input_adoption_readonly.py

★ SELECT 만, READ ONLY 트랜잭션. 출력은 집계뿐 — 농장명·id·이메일·좌표를 찍지 않는다.
★ 프로덕션 쓰기 0. 결과를 문서에 옮길 때도 집계 숫자만 옮긴다.
"""
import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

Q = {
 "farms_by_class_origin": """
   SELECT data_classification, data_origin, count(*) n,
          count(*) FILTER (WHERE active) active
   FROM farms GROUP BY 1,2 ORDER BY 1,2""",
 "live_farm_activity_90d": """
   WITH lf AS (SELECT id FROM farms WHERE data_classification='live_customer' AND active),
   ev AS (
     SELECT farm_id, max(d) last_d, count(*) n FROM (
       SELECT farm_id, mating_date d FROM matings WHERE deleted_at IS NULL
       UNION ALL SELECT farm_id, farrowing_date FROM farrowings WHERE deleted_at IS NULL
       UNION ALL SELECT farm_id, weaning_date FROM weanings WHERE deleted_at IS NULL) x
     GROUP BY farm_id)
   SELECT
     count(*) live_farms,
     count(*) FILTER (WHERE ev.n IS NOT NULL) farms_with_any_repro_event,
     count(*) FILTER (WHERE ev.last_d >= current_date - 90) farms_with_event_last_90d,
     count(*) FILTER (WHERE ev.last_d >= current_date - 30) farms_with_event_last_30d
   FROM lf LEFT JOIN ev ON ev.farm_id = lf.id""",
 "live_farm_event_created_recent": """
   SELECT count(DISTINCT farm_id) farms_created_event_last_30d
   FROM (SELECT farm_id, created_at FROM matings UNION ALL SELECT farm_id, created_at FROM farrowings
         UNION ALL SELECT farm_id, created_at FROM weanings) x
   JOIN farms f ON f.id = x.farm_id
   WHERE f.data_classification='live_customer' AND x.created_at >= now() - interval '30 days'""",
 "live_farm_sows": """
   SELECT count(DISTINCT s.farm_id) live_farms_with_sows, count(*) sows
   FROM sows s JOIN farms f ON f.id=s.farm_id
   WHERE f.data_classification='live_customer' AND s.deleted_at IS NULL""",
 "finisher_groups_by_class": """
   SELECT f.data_classification,
          count(g.id) groups_total,
          count(g.id) FILTER (WHERE g.end_date IS NULL) open_groups,
          count(g.id) FILTER (WHERE g.end_date IS NOT NULL) closed_groups,
          count(DISTINCT g.farm_id) farms_with_groups,
          count(DISTINCT g.farm_id) FILTER (WHERE g.end_date IS NULL) farms_with_open_group,
          count(g.id) FILTER (WHERE g.avg_entry_weight_kg IS NOT NULL) with_entry_wt,
          count(g.id) FILTER (WHERE g.avg_exit_weight_kg IS NOT NULL) with_exit_wt
   FROM farms f LEFT JOIN finisher_groups g ON g.farm_id=f.id AND g.deleted_at IS NULL
   WHERE f.active GROUP BY 1 ORDER BY 1""",
 "feed_records_all": """
   SELECT count(*) total, count(*) FILTER (WHERE deleted_at IS NULL) live FROM feed_records""",
 "audit_feed_actions": """
   SELECT action, count(*) FROM audit_log WHERE entity_type ILIKE '%feed%' GROUP BY 1""",
 "farm_users_entry_roles": """
   SELECT count(DISTINCT fm.user_id) users_with_entry_role, count(DISTINCT fm.farm_id) live_farms_with_entry_user
   FROM user_farms fm JOIN farms f ON f.id=fm.farm_id JOIN users u ON u.id=fm.user_id
   WHERE f.data_classification='live_customer' AND f.active
     AND coalesce(fm.role_override, u.system_role) IN ('FARM_OWNER','FARM_MANAGER','FARM_WORKER')""",
 "users_last_login_live": """
   SELECT count(DISTINCT u.id) FILTER (WHERE u.last_login_at >= now() - interval '30 days') users_login_30d,
          count(DISTINCT u.id) FILTER (WHERE u.last_login_at >= now() - interval '90 days') users_login_90d,
          count(DISTINCT u.id) users_total
   FROM users u JOIN user_farms fm ON fm.user_id=u.id JOIN farms f ON f.id=fm.farm_id
   WHERE f.data_classification='live_customer' AND u.active""",
 "events_created_90d_by_class": """
   SELECT f.data_classification, x.kind, count(*) n, count(DISTINCT x.farm_id) farms
   FROM (SELECT farm_id, 'mating' kind, created_at FROM matings UNION ALL
         SELECT farm_id, 'farrowing', created_at FROM farrowings UNION ALL
         SELECT farm_id, 'weaning', created_at FROM weanings UNION ALL
         SELECT farm_id, 'finisher_group', created_at FROM finisher_groups) x
   JOIN farms f ON f.id=x.farm_id
   WHERE x.created_at >= now() - interval '90 days' GROUP BY 1,2 ORDER BY 1,2""",
 "farm_currency": """
   SELECT coalesce(currency,'<NULL>') currency, count(*) FROM farms WHERE active GROUP BY 1 ORDER BY 2 DESC""",
 "farm_countries_live": """
   SELECT country, count(*) FROM farms WHERE active AND data_classification='live_customer' GROUP BY 1 ORDER BY 2 DESC""",
}


async def main() -> None:
    url = os.environ["DATABASE_URL"]
    eng = create_async_engine(url, pool_pre_ping=True)
    async with eng.connect() as conn:
        await conn.execute(text("SET TRANSACTION READ ONLY"))
        for name, sql in Q.items():
            try:
                rows = (await conn.execute(text(sql))).mappings().all()
                print(f"== {name}")
                for r in rows:
                    print("   ", dict(r))
            except Exception as e:  # column/table name mismatch → report, keep going
                print(f"== {name}  ERROR {type(e).__name__}: {str(e).splitlines()[0][:160]}")
                await conn.rollback()
                await conn.execute(text("SET TRANSACTION READ ONLY"))
    await eng.dispose()


asyncio.run(main())
