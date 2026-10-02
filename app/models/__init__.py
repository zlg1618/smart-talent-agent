from app.models.base import Base, TimestampMixin
from app.models.compensation import (
    BenefitPlan,
    EmployeeBenefit,
    EmployeeCompensation,
    SalaryBand,
)
from app.models.development import Course, DepartmentMetric, IDP
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
from app.models.talent import KeyPosition, SuccessionPlan
from app.models.workforce import AttritionRisk, HeadcountPlan, WorkforceForecast

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
        "KeyPosition",
        "SuccessionPlan",
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
    "Course",
    "DepartmentMetric",
    "Employee",
    "EmployeeBenefit",
    "EmployeeCompensation",
    "EmployeeCompetency",
    "EngagementSurvey",
    "HeadcountPlan",
    "HRIS_MODULES",
    "IDP",
    "ImprovementPlan",
    "InterviewSchedule",
    "JobPost",
    "KeyPosition",
    "LeaveRequest",
    "OfferRecord",
    "PerformanceGoal",
    "PerformanceRecord",
    "PerformanceReview",
    "PotentialAssessment",
    "RelationCase",
    "SalaryBand",
    "SuccessionPlan",
    "TimestampMixin",
    "TrainingCourse",
    "TrainingEnrollment",
    "WorkforceForecast",
]
