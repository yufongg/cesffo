from sqlalchemy import select, text

from db.db import engine, Base, get_db_session
import model.models  # noqa: F401  -- registers the models on Base.metadata
from model.models import User, Category, Course, CourseEnrollment
from user.auth import hash_password


# --- Schema -----------------------------------------------------------------
SCHEMA_MIGRATIONS = [
    'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE',
    'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS force_password_reset BOOLEAN NOT NULL DEFAULT FALSE',
]


def ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for statement in SCHEMA_MIGRATIONS:
            conn.execute(text(statement))

#! The password is plaintext but i import the same hasher. So it should workthe same
USERS = [
    {"key": "admin",      "email": "admin@cesffo.io",      "username": "admin_kai",    "role": "admin",      "password": "CesffoAdmin#2026"},
    {"key": "instructor", "email": "instructor@cesffo.io", "username": "prof_lena",    "role": "instructor", "password": "TeachWell#2026"},
    {"key": "demo",       "email": "student@cesffo.io",    "username": "demo_student", "role": "student",    "password": "LearnMoney#2026"},
    {"key": "alex",       "email": "alex@cesffo.io",       "username": "alex_tan",     "role": "student",    "password": "SaverGoals2026"},
    {"key": "maria",      "email": "maria@cesffo.io",      "username": "maria_lim",    "role": "student",    "password": "BudgetWins2026"},
]

#! Jon can change this if needed
CATEGORIES = [
    {"name": "Budgeting Basics", "slug": "budgeting-basics", "description": "Day-to-day money management and budgeting habits.", "display_order": 1},
    {"name": "Saving & Investing", "slug": "saving-investing", "description": "Growing wealth through saving and investing.", "display_order": 2},
    {"name": "Debt & Credit", "slug": "debt-credit", "description": "Managing debt and building healthy credit.", "display_order": 3},
    {"name": "Retirement & Planning", "slug": "retirement-planning", "description": "Long-term financial planning.", "display_order": 4},
]

#! If required Jon can change this info, table and columns.
COURSES = [
    {"name": "Budgeting 101: Take Control of Your Money", "level": "Beginner",     "tags": ["Budgeting", "Personal Finance"], "summary": "Build your first budget, track spending, and put every dollar to work."},
    {"name": "Building an Emergency Fund",                "level": "Beginner",     "tags": ["Saving", "Budgeting"],            "summary": "Why a safety net matters and a step-by-step plan to build one."},
    {"name": "Understanding Credit Scores",              "level": "Beginner",     "tags": ["Credit", "Debt"],                 "summary": "What drives your credit score and how to improve it responsibly."},
    {"name": "Getting Out of Debt",                      "level": "Intermediate", "tags": ["Debt", "Personal Finance"],       "summary": "Compare the snowball and avalanche methods and build a payoff plan."},
    {"name": "Investing Fundamentals",                   "level": "Beginner",     "tags": ["Investing", "Stocks"],            "summary": "Risk, return, compounding, and how markets actually work."},
    {"name": "Index Funds & ETFs Explained",            "level": "Intermediate", "tags": ["Investing", "Stocks"],            "summary": "Low-cost, diversified investing for the long term."},
    {"name": "Retirement Planning Essentials",          "level": "Intermediate", "tags": ["Retirement", "Investing"],        "summary": "Accounts, contributions, and the power of starting early."},
    {"name": "Taxes Made Simple",                        "level": "Beginner",     "tags": ["Taxes", "Personal Finance"],      "summary": "Understand how income tax works and keep more of what you earn."},
    {"name": "Intro to Cryptocurrency & Risk",          "level": "Advanced",     "tags": ["Crypto", "Investing"],            "summary": "How crypto works, the real risks, and how to evaluate it soberly."},
    {"name": "Building Multiple Income Streams",        "level": "Advanced",     "tags": ["Income", "Entrepreneurship"],     "summary": "Side income, freelancing, and turning skills into earnings."},
]

# Which courses each student is enrolled in, with progress (0.0 - 1.0).
ENROLLMENTS = {
    "demo":  [("Budgeting 101: Take Control of Your Money", 0.65),
              ("Understanding Credit Scores", 0.20),
              ("Investing Fundamentals", 1.0)],
    "alex":  [("Budgeting 101: Take Control of Your Money", 0.4),
              ("Investing Fundamentals", 0.8),
              ("Index Funds & ETFs Explained", 0.1)],
    "maria": [("Building an Emergency Fund", 0.5),
              ("Getting Out of Debt", 0.3),
              ("Retirement Planning Essentials", 0.15),
              ("Taxes Made Simple", 0.9)],
}


# --- get-or-create helpers --------------------------------------------------
def get_or_create_user(session, spec) -> User:
    user = session.scalar(select(User).where(User.email == spec["email"]))
    if user:
        return user
    user = User(
        email=spec["email"],
        username=spec["username"],
        role=spec["role"],
        password=hash_password(spec["password"]),
        is_active=True,
    )
    session.add(user)
    session.flush()
    return user


def get_or_create_category(session, spec) -> Category:
    cat = session.scalar(select(Category).where(Category.slug == spec["slug"]))
    if cat:
        return cat
    cat = Category(
        name=spec["name"],
        slug=spec["slug"],
        description=spec["description"],
        display_order=spec["display_order"],
    )
    session.add(cat)
    session.flush()
    return cat


def get_or_create_course(session, spec, instructor_id) -> Course:
    course = session.scalar(select(Course).where(Course.course_name == spec["name"]))
    if course:
        return course
    course = Course(
        instructor_id=instructor_id,
        course_name=spec["name"],
        # Ready for richer content later: text lessons + interactive quizzes.
        content={"summary": spec["summary"], "modules": []},
        tags=spec["tags"],
        prerequirements={"level": spec["level"]},
    )
    session.add(course)
    session.flush()
    return course


def get_or_create_enrollment(session, course_id, student_id, progress) -> None:
    existing = session.scalar(
        select(CourseEnrollment).where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.student_id == student_id,
        )
    )
    if existing:
        return
    session.add(CourseEnrollment(
        course_id=course_id,
        student_id=student_id,
        progress=progress,
        dropped=False,
    ))


def seed() -> None:
    ensure_schema()

    with get_db_session() as session:
        users = {spec["key"]: get_or_create_user(session, spec) for spec in USERS}

        for spec in CATEGORIES:
            get_or_create_category(session, spec)

        instructor_id = users["instructor"].user_id
        courses = {spec["name"]: get_or_create_course(session, spec, instructor_id) for spec in COURSES}

        for student_key, enrolls in ENROLLMENTS.items():
            student_id = users[student_key].user_id
            for course_name, progress in enrolls:
                get_or_create_enrollment(session, courses[course_name].course_id, student_id, progress)
        # context manager commits on exit

    print("\n  Seed complete.\n")
    print(f"  Users:    {len(USERS)}")
    print(f"  Courses:  {len(COURSES)}")
    print(f"  Topics:   {len(CATEGORIES)}")
    print("\n  Test logins (email / password):")
    for spec in USERS:
        print(f"    [{spec['role']:>10}]  {spec['email']:<24}  {spec['password']}")
    print()


if __name__ == "__main__":
    seed()
