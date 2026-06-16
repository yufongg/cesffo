"""Idempotent demo-content seed for FR-06/FR-07: modules, reading material, and
quiz activities attached to the 6 existing marketplace courses.

Run AFTER seed.py (which creates the courses + instructor "prof_lena"). This
script never creates courses — it only matches existing Course rows by name
and attaches content to them, going through the same Pydantic validation +
nh3 sanitization the instructor-authoring API uses (course/instructor_router.py),
so seed data can never bypass the SR-09 stored-XSS controls.

Usage:
    docker compose exec -T backend python seed_course_content.py
"""
from sqlalchemy import select

from db.db import engine, Base, get_db_session
import model.models  # noqa: F401  -- registers the models on Base.metadata
from model.models import Course, Module, ReadingMaterial, InteractiveActivity, ActivityOption, User
from common.sanitize import sanitize_html, strip_tags
from course.instructor_router import ModuleCreate, ReadingMaterialCreate, InteractiveActivityCreate, ActivityOptionInput

INSTRUCTOR_USERNAME = "prof_lena"

# --- Demo content -------------------------------------------------------
# Each course: 3-4 short modules with one reading material, plus a final
# "quiz" module with one mcq_single, one mcq_multi, and one short_answer
# activity (correct answers stored server-side only).
COURSE_CONTENT = {
    "Budgeting 101: Take Control of Your Money": {
        "modules": [
            {
                "title": "What Is a Budget?",
                "materials": [{
                    "title": "Why Budgeting Matters",
                    "body": "<p>A budget is simply a plan for your money: it tells every dollar where to go "
                            "before you spend it. Without one, spending tends to expand to fill whatever "
                            "income is available. Tracking income and expenses for a single month is the "
                            "fastest way to see where your money actually goes.</p>",
                }],
            },
            {
                "title": "The 50/30/20 Rule",
                "materials": [{
                    "title": "A Simple Way to Split Your Income",
                    "body": "<p>The 50/30/20 rule allocates take-home pay into three buckets: 50% to needs "
                            "(rent, groceries, utilities), 30% to wants (dining out, entertainment), and 20% "
                            "to savings and debt repayment. It's a starting point, not a strict law &mdash; "
                            "adjust the splits to fit your situation.</p>",
                }],
            },
            {
                "title": "Tracking Your Spending",
                "materials": [{
                    "title": "Tools That Make Tracking Easy",
                    "body": "<p>You can track spending with a notebook, a spreadsheet, a budgeting app, or "
                            "the classic envelope system (cash divided into labelled envelopes per category). "
                            "The best tool is whichever one you'll actually keep using every week.</p>",
                }],
            },
            {
                "title": "Budgeting Quiz",
                "activities": [
                    {
                        "title": "50/30/20 Allocation",
                        "activity_type": "mcq_single",
                        "prompt": "In the 50/30/20 rule, what share of income is recommended for savings and debt repayment?",
                        "options": [
                            {"option_text": "50%", "is_correct": False},
                            {"option_text": "30%", "is_correct": False},
                            {"option_text": "20%", "is_correct": True},
                            {"option_text": "10%", "is_correct": False},
                        ],
                    },
                    {
                        "title": "Budgeting Methods",
                        "activity_type": "mcq_multi",
                        "prompt": "Which of these are common budgeting methods? (select all that apply)",
                        "options": [
                            {"option_text": "Zero-based budgeting", "is_correct": True},
                            {"option_text": "Envelope system", "is_correct": True},
                            {"option_text": "50/30/20 rule", "is_correct": True},
                            {"option_text": "Compound interest", "is_correct": False},
                        ],
                    },
                    {
                        "title": "Needs Allocation",
                        "activity_type": "short_answer",
                        "prompt": "In the 50/30/20 rule, what percentage of income is recommended for needs? (number only)",
                        "correct_answers": ["50", "50%"],
                    },
                ],
            },
        ],
    },
    "Investing Fundamentals": {
        "modules": [
            {
                "title": "Risk and Return",
                "materials": [{
                    "title": "Why Risk and Reward Move Together",
                    "body": "<p>Investments that offer higher potential returns generally carry higher risk "
                            "of loss. Cash is the safest but barely grows; stocks can lose value short-term "
                            "but have historically outpaced inflation over the long run.</p>",
                }],
            },
            {
                "title": "The Power of Compounding",
                "materials": [{
                    "title": "Earning Returns on Your Returns",
                    "body": "<p>Compounding means your investment gains start earning their own gains. "
                            "The earlier you start investing, the more time compounding has to work, which "
                            "is why even small amounts invested young can outgrow larger amounts invested late.</p>",
                }],
            },
            {
                "title": "How Markets Work",
                "materials": [{
                    "title": "Buyers, Sellers, and Prices",
                    "body": "<p>A stock represents partial ownership of a company. Exchanges match buyers "
                            "and sellers, and prices move based on supply, demand, and expectations about a "
                            "company's future earnings.</p>",
                }],
            },
            {
                "title": "Investing Quiz",
                "activities": [
                    {
                        "title": "Risk vs Return",
                        "activity_type": "mcq_single",
                        "prompt": "Generally speaking, what is the relationship between risk and potential return?",
                        "options": [
                            {"option_text": "Higher risk usually means higher potential return", "is_correct": True},
                            {"option_text": "There is no relationship", "is_correct": False},
                            {"option_text": "Lower risk always means higher return", "is_correct": False},
                            {"option_text": "Risk and return are always equal", "is_correct": False},
                        ],
                    },
                    {
                        "title": "Asset Classes",
                        "activity_type": "mcq_multi",
                        "prompt": "Which of these are common investment asset classes? (select all that apply)",
                        "options": [
                            {"option_text": "Stocks", "is_correct": True},
                            {"option_text": "Bonds", "is_correct": True},
                            {"option_text": "Real estate", "is_correct": True},
                            {"option_text": "Lottery tickets", "is_correct": False},
                        ],
                    },
                    {
                        "title": "Compounding Basics",
                        "activity_type": "short_answer",
                        "prompt": "Fill in the blank: compounding means your investment gains start earning their own ______.",
                        "correct_answers": ["gains", "returns"],
                    },
                ],
            },
        ],
    },
    "Building an Emergency Fund": {
        "modules": [
            {
                "title": "Why You Need a Safety Net",
                "materials": [{
                    "title": "Life Happens",
                    "body": "<p>An emergency fund covers unplanned costs &mdash; a job loss, a medical bill, "
                            "a car repair &mdash; without forcing you into high-interest debt. It's the "
                            "foundation that makes the rest of a financial plan possible.</p>",
                }],
            },
            {
                "title": "How Much to Save",
                "materials": [{
                    "title": "Picking a Target",
                    "body": "<p>Most experts recommend 3-6 months of essential expenses (rent, food, "
                            "utilities, minimum debt payments). Start with a smaller goal, like $500 or one "
                            "month of expenses, and build from there.</p>",
                }],
            },
            {
                "title": "Where to Keep It",
                "materials": [{
                    "title": "Accessible but Separate",
                    "body": "<p>Keep emergency savings somewhere safe and liquid, like a high-yield savings "
                            "account or money market account &mdash; not invested in stocks, where the "
                            "balance could be down right when you need it.</p>",
                }],
            },
            {
                "title": "Emergency Fund Quiz",
                "activities": [
                    {
                        "title": "Recommended Size",
                        "activity_type": "mcq_single",
                        "prompt": "How many months of essential expenses do most experts recommend keeping in an emergency fund?",
                        "options": [
                            {"option_text": "1 month", "is_correct": False},
                            {"option_text": "3-6 months", "is_correct": True},
                            {"option_text": "12 months", "is_correct": False},
                            {"option_text": "None needed", "is_correct": False},
                        ],
                    },
                    {
                        "title": "Where to Keep It",
                        "activity_type": "mcq_multi",
                        "prompt": "Which of these are good places to keep an emergency fund? (select all that apply)",
                        "options": [
                            {"option_text": "High-yield savings account", "is_correct": True},
                            {"option_text": "Money market account", "is_correct": True},
                            {"option_text": "Long-term stock investments", "is_correct": False},
                            {"option_text": "Cryptocurrency", "is_correct": False},
                        ],
                    },
                    {
                        "title": "Purpose of the Fund",
                        "activity_type": "short_answer",
                        "prompt": "Fill in the blank: an emergency fund should primarily cover ______ expenses.",
                        "correct_answers": ["unexpected", "emergency"],
                    },
                ],
            },
        ],
    },
    "Understanding Credit Scores": {
        "modules": [
            {
                "title": "What Is a Credit Score?",
                "materials": [{
                    "title": "A Number Lenders Trust",
                    "body": "<p>A credit score summarizes how risky you look to lenders based on your "
                            "borrowing and repayment history. Higher scores typically unlock lower interest "
                            "rates on loans, credit cards, and even some rental applications.</p>",
                }],
            },
            {
                "title": "Factors That Affect Your Score",
                "materials": [{
                    "title": "What Goes Into the Number",
                    "body": "<p>Payment history matters most, followed by credit utilization (how much of "
                            "your available credit you're using), length of credit history, credit mix, and "
                            "new credit inquiries.</p>",
                }],
            },
            {
                "title": "Building Good Credit Habits",
                "materials": [{
                    "title": "Small Habits, Big Impact",
                    "body": "<p>Pay every bill on time, keep credit card balances well below their limits, "
                            "avoid opening many new accounts at once, and check your credit report regularly "
                            "for errors.</p>",
                }],
            },
            {
                "title": "Credit Score Quiz",
                "activities": [
                    {
                        "title": "Biggest Factor",
                        "activity_type": "mcq_single",
                        "prompt": "Which factor typically has the biggest impact on your credit score?",
                        "options": [
                            {"option_text": "Payment history", "is_correct": True},
                            {"option_text": "Number of credit inquiries", "is_correct": False},
                            {"option_text": "The type of phone you own", "is_correct": False},
                            {"option_text": "Your income", "is_correct": False},
                        ],
                    },
                    {
                        "title": "Good Habits",
                        "activity_type": "mcq_multi",
                        "prompt": "Which of these actions can help improve your credit score? (select all that apply)",
                        "options": [
                            {"option_text": "Paying bills on time", "is_correct": True},
                            {"option_text": "Keeping credit utilization low", "is_correct": True},
                            {"option_text": "Maxing out credit cards", "is_correct": False},
                            {"option_text": "Opening many new accounts at once", "is_correct": False},
                        ],
                    },
                    {
                        "title": "FICO Range",
                        "activity_type": "short_answer",
                        "prompt": "What is the standard FICO credit score range, from lowest to highest? (e.g. 300-850)",
                        "correct_answers": ["300-850", "300 to 850"],
                    },
                ],
            },
        ],
    },
    "Getting Out of Debt": {
        "modules": [
            {
                "title": "Understanding Your Debt",
                "materials": [{
                    "title": "List It All Out",
                    "body": "<p>Before choosing a payoff strategy, list every debt with its balance, "
                            "interest rate, and minimum payment. Seeing the full picture makes the plan "
                            "feel achievable instead of overwhelming.</p>",
                }],
            },
            {
                "title": "The Snowball Method",
                "materials": [{
                    "title": "Smallest Balance First",
                    "body": "<p>The debt snowball pays minimums on everything, then throws extra money at "
                            "the smallest balance first. Each payoff builds momentum and motivation, even if "
                            "it isn't always the cheapest path mathematically.</p>",
                }],
            },
            {
                "title": "The Avalanche Method",
                "materials": [{
                    "title": "Highest Interest Rate First",
                    "body": "<p>The debt avalanche pays minimums on everything, then puts extra money toward "
                            "the highest-interest debt first. It usually saves the most money and time "
                            "overall, but requires more patience before the first debt disappears.</p>",
                }],
            },
            {
                "title": "Debt Payoff Quiz",
                "activities": [
                    {
                        "title": "Snowball Order",
                        "activity_type": "mcq_single",
                        "prompt": "The debt snowball method prioritizes paying off debts in which order?",
                        "options": [
                            {"option_text": "Smallest balance first", "is_correct": True},
                            {"option_text": "Highest interest rate first", "is_correct": False},
                            {"option_text": "Largest balance first", "is_correct": False},
                            {"option_text": "Random order", "is_correct": False},
                        ],
                    },
                    {
                        "title": "Valid Strategies",
                        "activity_type": "mcq_multi",
                        "prompt": "Which of these are valid debt payoff strategies? (select all that apply)",
                        "options": [
                            {"option_text": "Debt snowball", "is_correct": True},
                            {"option_text": "Debt avalanche", "is_correct": True},
                            {"option_text": "Debt consolidation", "is_correct": True},
                            {"option_text": "Ignoring the debt", "is_correct": False},
                        ],
                    },
                    {
                        "title": "Avalanche Recall",
                        "activity_type": "short_answer",
                        "prompt": "Which debt payoff method prioritizes the highest interest rate first? (one word)",
                        "correct_answers": ["avalanche", "debt avalanche"],
                    },
                ],
            },
        ],
    },
    "Index Funds & ETFs Explained": {
        "modules": [
            {
                "title": "What Is an Index Fund?",
                "materials": [{
                    "title": "Owning the Whole Market",
                    "body": "<p>An index fund holds a basket of investments designed to track a market "
                            "index, like the S&amp;P 500, instead of trying to beat it through active stock "
                            "picking. That makes it a simple way to own a diversified slice of the market.</p>",
                }],
            },
            {
                "title": "ETFs vs Mutual Funds",
                "materials": [{
                    "title": "Two Wrappers, Similar Goal",
                    "body": "<p>An exchange-traded fund (ETF) trades on an exchange throughout the day like "
                            "a stock, while a traditional mutual fund only prices once per day after markets "
                            "close. Both can track the same index.</p>",
                }],
            },
            {
                "title": "Why Diversification Matters",
                "materials": [{
                    "title": "Don't Put All Your Eggs in One Basket",
                    "body": "<p>Spreading money across many companies and sectors reduces the damage any "
                            "single company's bad news can do to your portfolio. Index funds give broad "
                            "diversification in a single purchase.</p>",
                }],
            },
            {
                "title": "Index Fund Quiz",
                "activities": [
                    {
                        "title": "Index Fund Goal",
                        "activity_type": "mcq_single",
                        "prompt": "What does an index fund aim to do?",
                        "options": [
                            {"option_text": "Beat the market through active trading", "is_correct": False},
                            {"option_text": "Track the performance of a market index", "is_correct": True},
                            {"option_text": "Guarantee a fixed return", "is_correct": False},
                            {"option_text": "Invest only in one company", "is_correct": False},
                        ],
                    },
                    {
                        "title": "Index Fund Benefits",
                        "activity_type": "mcq_multi",
                        "prompt": "Which of these are benefits commonly associated with index funds? (select all that apply)",
                        "options": [
                            {"option_text": "Low fees", "is_correct": True},
                            {"option_text": "Broad diversification", "is_correct": True},
                            {"option_text": "Guaranteed profits", "is_correct": False},
                            {"option_text": "No market risk", "is_correct": False},
                        ],
                    },
                    {
                        "title": "ETF Acronym",
                        "activity_type": "short_answer",
                        "prompt": "What three-letter acronym refers to a fund that trades on an exchange like a stock?",
                        "correct_answers": ["etf"],
                    },
                ],
            },
        ],
    },
}


# --- get-or-create helpers (validate through the same schemas + sanitizers
# the instructor-authoring API uses, so seed content can't bypass SR-09) ---
def get_instructor(session) -> User:
    instructor = session.scalar(select(User).where(User.username == INSTRUCTOR_USERNAME))
    if not instructor:
        raise RuntimeError(
            f"Instructor '{INSTRUCTOR_USERNAME}' not found — run `python seed.py` first."
        )
    return instructor


def get_or_create_module(session, course_id, spec, order_index) -> Module:
    validated = ModuleCreate(title=spec["title"], description=spec.get("description"), order_index=order_index)
    module = session.scalar(
        select(Module).where(Module.course_id == course_id, Module.title == validated.title)
    )
    if module:
        return module
    module = Module(
        course_id=course_id,
        title=strip_tags(validated.title),
        description=sanitize_html(validated.description) if validated.description else None,
        order_index=validated.order_index,
    )
    session.add(module)
    session.flush()
    return module


def get_or_create_material(session, module_id, spec, order_index) -> ReadingMaterial:
    validated = ReadingMaterialCreate(title=spec["title"], body=spec["body"], order_index=order_index)
    material = session.scalar(
        select(ReadingMaterial).where(ReadingMaterial.module_id == module_id, ReadingMaterial.title == validated.title)
    )
    if material:
        return material
    material = ReadingMaterial(
        module_id=module_id,
        title=strip_tags(validated.title),
        body=sanitize_html(validated.body),
        order_index=validated.order_index,
    )
    session.add(material)
    session.flush()
    return material


def get_or_create_activity(session, module_id, spec, order_index) -> InteractiveActivity:
    options = [ActivityOptionInput(**o) for o in spec["options"]] if spec.get("options") else None
    validated = InteractiveActivityCreate(
        title=spec["title"],
        activity_type=spec["activity_type"],
        prompt=spec["prompt"],
        order_index=order_index,
        options=options,
        correct_answers=spec.get("correct_answers"),
    )
    activity = session.scalar(
        select(InteractiveActivity).where(InteractiveActivity.module_id == module_id, InteractiveActivity.title == validated.title)
    )
    if activity:
        return activity
    activity = InteractiveActivity(
        module_id=module_id,
        title=strip_tags(validated.title),
        activity_type=validated.activity_type,
        prompt=sanitize_html(validated.prompt),
        order_index=validated.order_index,
        correct_answers=[strip_tags(a) for a in validated.correct_answers] if validated.correct_answers else None,
    )
    if validated.options:
        activity.options = [
            ActivityOption(option_text=strip_tags(o.option_text), is_correct=o.is_correct, order_index=i)
            for i, o in enumerate(validated.options)
        ]
    session.add(activity)
    session.flush()
    return activity


def seed_course_content() -> None:
    Base.metadata.create_all(bind=engine)

    modules_created = materials_created = activities_created = 0
    skipped_courses = []

    with get_db_session() as session:
        instructor = get_instructor(session)

        for course_name, spec in COURSE_CONTENT.items():
            course = session.scalar(select(Course).where(Course.course_name == course_name))
            if not course:
                skipped_courses.append(course_name)
                continue
            if course.instructor_id != instructor.user_id:
                print(f"  WARNING: {course_name!r} is not owned by {INSTRUCTOR_USERNAME!r}; leaving ownership unchanged.")

            for i, module_spec in enumerate(spec["modules"]):
                before = session.scalar(
                    select(Module).where(Module.course_id == course.course_id, Module.title == module_spec["title"])
                )
                module = get_or_create_module(session, course.course_id, module_spec, i)
                if before is None:
                    modules_created += 1

                for j, material_spec in enumerate(module_spec.get("materials", [])):
                    before = session.scalar(
                        select(ReadingMaterial).where(ReadingMaterial.module_id == module.module_id, ReadingMaterial.title == material_spec["title"])
                    )
                    get_or_create_material(session, module.module_id, material_spec, j)
                    if before is None:
                        materials_created += 1

                for k, activity_spec in enumerate(module_spec.get("activities", [])):
                    before = session.scalar(
                        select(InteractiveActivity).where(InteractiveActivity.module_id == module.module_id, InteractiveActivity.title == activity_spec["title"])
                    )
                    get_or_create_activity(session, module.module_id, activity_spec, k)
                    if before is None:
                        activities_created += 1
        # context manager commits on exit

    print("\n  Course content seed complete.\n")
    print(f"  Modules created:    {modules_created}")
    print(f"  Materials created:  {materials_created}")
    print(f"  Activities created: {activities_created}")
    if skipped_courses:
        print("\n  SKIPPED (no matching course found — run seed.py first):")
        for name in skipped_courses:
            print(f"    - {name}")
    print()


if __name__ == "__main__":
    seed_course_content()
