from app.models.base import Base, TimestampMixin
from app.models.compensation import (
    BenefitPlan,
    EmployeeBenefit,
    EmployeeCompensation,
    SalaryBand,
)
from app.models.employee import (
    Competency,
    Employee,
    EmployeeCompetency,
    PerformanceRecord,
    PotentialAssessment,
)
from app.models.employee_relations import (
    AttendanceRecord,
    EngagementSurvey,
    LeaveRequest,
    RelationCase,
)
from app.models.learning import TrainingCourse, TrainingEnrollment
from app.models.organization import (
    JobArchitecture,
    OrgChange,
    OrgEffectiveness,
    OrgUnit,
)
from app.models.performance import (
    CalibrationSession,
    ImprovementPlan,
    PerformanceGoal,
    PerformanceReview,
)
from app.models.recruitment import (
    Application,
    Candidate,
    CandidateSkill,
    InterviewSchedule,
    JobPost,
    OfferRecord,
)
from app.models.talent_development import (
    DevelopmentProgram,
    Mentorship,
    TalentPool,
    TalentStandard,
)
from app.models.workforce import AttritionRisk, HeadcountPlan, WorkforceForecast

# 核心双域：组织发展 + 人才发展
CORE_MODULES: dict[str, list[str]] = {
    "organization_development": [
        "OrgUnit",
        "OrgEffectiveness",
        "JobArchitecture",
        "OrgChange",
    ],
    "talent_development": [
        "TalentStandard",
        "TalentPool",
        "DevelopmentProgram",
        "Mentorship",
    ],
}

# HRIS 六大模块及其模型清单，供 Adapters 与文档按域遍历
HRIS_MODULES: dict[str, list[str]] = {
    "recruitment": [
        "JobPost",
        "Candidate",
        "CandidateSkill",
        "Application",
        "InterviewSchedule",
        "OfferRecord",
    ],
    "compensation": [
        "SalaryBand",
        "EmployeeCompensation",
        "BenefitPlan",
        "EmployeeBenefit",
    ],
    "performance": [
        "PerformanceRecord",
        "PerformanceGoal",
        "PerformanceReview",
        "CalibrationSession",
        "ImprovementPlan",
    ],
    "employee_relations": [
        "LeaveRequest",
        "AttendanceRecord",
        "RelationCase",
        "EngagementSurvey",
    ],
    "learning": [
        "TrainingCourse",
        "TrainingEnrollment",
        "Competency",
        "EmployeeCompetency",
    ],
    "workforce": [
        "HeadcountPlan",
        "WorkforceForecast",
        "AttritionRisk",
    ],
}

__all__ = [
    "Application",
    "AttritionRisk",
    "AttendanceRecord",
    "Base",
    "BenefitPlan",
    "CalibrationSession",
    "Candidate",
    "CandidateSkill",
    "Competency",
    "CORE_MODULES",
    "DevelopmentProgram",
    "Employee",
    "EmployeeBenefit",
    "EmployeeCompensation",
    "EmployeeCompetency",
    "EngagementSurvey",
    "HeadcountPlan",
    "HRIS_MODULES",
    "ImprovementPlan",
    "InterviewSchedule",
    "JobArchitecture",
    "JobPost",
    "LeaveRequest",
    "Mentorship",
    "OfferRecord",
    "OrgChange",
    "OrgEffectiveness",
    "OrgUnit",
    "PerformanceGoal",
    "PerformanceRecord",
    "PerformanceReview",
    "PotentialAssessment",
    "RelationCase",
    "SalaryBand",
    "TalentPool",
    "TalentStandard",
    "TimestampMixin",
    "TrainingCourse",
    "TrainingEnrollment",
    "WorkforceForecast",
]
