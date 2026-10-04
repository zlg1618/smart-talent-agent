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
    CultureSurvey,
    JobArchitecture,
    OrgChange,
    OrgEffectiveness,
    OrgHealthSurvey,
    OrgScan,
    OrgUnit,
    StrategicGoal,
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
    CompetencyLevel,
    DevelopmentPlan,
    DevelopmentProgram,
    KeyPosition,
    Mentorship,
    PositionCompetency,
    Review360,
    SuccessionCandidate,
    TalentPool,
    TalentStandard,
)
from app.models.workforce import AttritionRisk, HeadcountPlan, WorkforceForecast

# 核心双域：组织发展（OD）+ 人才发展（TD）
CORE_MODULES: dict[str, list[str]] = {
    "organization_development": [
        "OrgUnit",
        "OrgHealthSurvey",
        "OrgScan",
        "StrategicGoal",
        "CultureSurvey",
        "OrgEffectiveness",
        "JobArchitecture",
        "OrgChange",
    ],
    "talent_development": [
        "Review360",
        "CompetencyLevel",
        "PositionCompetency",
        "TalentStandard",
        "KeyPosition",
        "SuccessionCandidate",
        "TalentPool",
        "DevelopmentProgram",
        "DevelopmentPlan",
        "Mentorship",
    ],
}

# HRIS 六大支撑模块及其模型清单
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
    "CompetencyLevel",
    "CORE_MODULES",
    "CultureSurvey",
    "DevelopmentPlan",
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
    "KeyPosition",
    "LeaveRequest",
    "Mentorship",
    "OfferRecord",
    "OrgChange",
    "OrgEffectiveness",
    "OrgHealthSurvey",
    "OrgScan",
    "OrgUnit",
    "PerformanceGoal",
    "PerformanceRecord",
    "PerformanceReview",
    "PositionCompetency",
    "PotentialAssessment",
    "RelationCase",
    "Review360",
    "SalaryBand",
    "StrategicGoal",
    "SuccessionCandidate",
    "TalentPool",
    "TalentStandard",
    "TimestampMixin",
    "TrainingCourse",
    "TrainingEnrollment",
    "WorkforceForecast",
]
