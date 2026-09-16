"""UIQA 역할계정 비번 셋업(QA setup, uiqa_ 접두어 한정). 백엔드 자체 해셔 재사용 — 추측/직접해시 금지.
ORM은 모델-DB 스키마 드리프트(users.username 부재)로 못 씀 → 존재 컬럼만 raw SQL UPDATE.
일회용: 풀스펙 QA(RBAC A2/A3)용 5역할 로그인 활성화. 실행: api/.venv python _uiqa_setpw.py"""
import asyncio

from sqlalchemy import text

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal

EMAILS = [
    "uiqa_farm_owner@pigos.io", "uiqa_farm_manager@pigos.io",
    "uiqa_farm_worker@pigos.io", "uiqa_vet@pigos.io", "uiqa_viewer@pigos.io",
]


async def main():
    new_hash = hash_password("123123")
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            text("UPDATE users SET password_hash = :h WHERE email = ANY(:emails) RETURNING email, system_role"),
            {"h": new_hash, "emails": EMAILS},
        )
        rows = res.fetchall()
        await db.commit()
        for em, role in rows:
            print(f"  {em:30} role={role} SET")
        print(f"updated {len(rows)}/{len(EMAILS)}")


asyncio.run(main())
