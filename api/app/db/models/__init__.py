"""
Import all models here so Alembic autogenerate picks them up.
"""
from app.db.models.benchmark import (  # noqa: F401
    Benchmark,
    KpiDefinition,
    SourceObservation,
)
from app.db.models.config import (  # noqa: F401
    ComplianceProfile,
    DefaultMetricValue,
    FarmConfig,
    MarketDefault,
    MarketPriceReference,
    RegionDefault,
    ScopeKpiRecommendation,
)
from app.db.models.consent import ConsentRecord  # noqa: F401
from app.db.models.content import (  # noqa: F401
    Announcement,
    SupportReply,
    SupportTicket,
)
from app.db.models.events import (  # noqa: F401
    Farrowing,
    Mating,
    PigletEvent,
    PregnancyCheck,
    ReproductiveEvent,
    Weaning,
)
from app.db.models.feed_source import FeedSourceRow, FeedSourceSyncRun  # noqa: F401
from app.db.models.health import FeedRecord, HealthEvent, Removal  # noqa: F401
from app.db.models.kpi_policy import CountryKpiPolicy  # noqa: F401
from app.db.models.kpi_presentation import CountryKpiPresentation  # noqa: F401
from app.db.models.master import (  # noqa: F401
    DiseaseCode,
    EventDefinition,
    MedicationCatalog,
    VaccineCatalog,
)
from app.db.models.operational_default import OperationalDefault  # noqa: F401
from app.db.models.ops import (  # noqa: F401
    ApiKey,
    Device,
    FinisherGroup,
    KpiSnapshot,
    LlmUsageLog,
    Notification,
    PeriodLock,
    SyncConflictQueue,
    SyncLog,
    Task,
)
from app.db.models.pilot_signup import PilotSignup  # noqa: F401
from app.db.models.platform import (  # noqa: F401
    AddonSubscription,
    AuditLog,
    Farm,
    Organization,
    RefreshToken,
    SyncQueue,
    User,
    UserFarm,
)
from app.db.models.rule_config import RuleConfig  # noqa: F401
from app.db.models.sow import Boar, BreedingCycle, Building, Sow  # noqa: F401
