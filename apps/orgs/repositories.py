"""Django ORM implementations of org repository protocols."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from stripe_saas_core.domain.org import Org, OrgMember, OrgRole

from apps.orgs.models import Org as OrgModel
from apps.orgs.models import OrgMember as OrgMemberModel
from helpers import aget_or_none


class DjangoOrgRepository:
    @staticmethod
    def _to_domain(obj: OrgModel) -> Org:
        return Org(
            id=obj.id,
            name=obj.name,
            slug=obj.slug,
            logo_url=obj.logo_url,
            created_by=obj.created_by_id,
            created_at=obj.created_at,
            deleted_at=obj.deleted_at,
        )

    async def get_by_id(self, org_id: UUID) -> Org | None:
        return await aget_or_none(OrgModel, self._to_domain, id=org_id, deleted_at__isnull=True)

    async def get_by_slug(self, slug: str) -> Org | None:
        return await aget_or_none(OrgModel, self._to_domain, slug=slug, deleted_at__isnull=True)

    async def save(self, org: Org) -> Org:
        await OrgModel.objects.aupdate_or_create(
            id=org.id,
            defaults={
                "name": org.name,
                "slug": org.slug,
                "logo_url": org.logo_url,
                "created_by_id": org.created_by,
                "deleted_at": org.deleted_at,
            },
        )
        return org

    async def delete(self, org_id: UUID) -> None:
        await OrgModel.objects.filter(id=org_id).aupdate(deleted_at=datetime.now(UTC))


class DjangoOrgMemberRepository:
    @staticmethod
    def _to_domain(obj: OrgMemberModel) -> OrgMember:
        return OrgMember(
            id=obj.id,
            org_id=obj.org_id,
            user_id=obj.user_id,
            role=OrgRole(obj.role),
            is_billing=obj.is_billing,
            joined_at=obj.joined_at,
        )

    async def get(self, org_id: UUID, user_id: UUID) -> OrgMember | None:
        return await aget_or_none(OrgMemberModel, self._to_domain, org_id=org_id, user_id=user_id)

    async def list_by_org(self, org_id: UUID, limit: int = 500) -> list[OrgMember]:
        return [
            self._to_domain(obj)
            async for obj in OrgMemberModel.objects.filter(org_id=org_id)[:limit]
        ]

    async def list_by_user(self, user_id: UUID, limit: int = 500) -> list[OrgMember]:
        return [
            self._to_domain(obj)
            async for obj in OrgMemberModel.objects.filter(user_id=user_id)[:limit]
        ]

    async def save(self, member: OrgMember) -> OrgMember:
        await OrgMemberModel.objects.aupdate_or_create(
            id=member.id,
            defaults={
                "org_id": member.org_id,
                "user_id": member.user_id,
                "role": member.role.value,
                "is_billing": member.is_billing,
            },
        )
        return member

    async def delete(self, org_id: UUID, user_id: UUID) -> None:
        await OrgMemberModel.objects.filter(org_id=org_id, user_id=user_id).adelete()

    async def count_active(self, org_id: UUID) -> int:
        return await OrgMemberModel.objects.filter(org_id=org_id).acount()
