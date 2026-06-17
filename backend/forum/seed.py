from sqlalchemy import select

from db.db import get_db_session
from model.models import Category, Thread, Post


def seed_forum_demo_data() -> None:
    """Creates demo forum categories and starter threads when the forum is empty."""
    with get_db_session() as session:
        existing_category = session.scalar(select(Category))
        if existing_category:
            return

        category_data = [
            {
                "name": "Budgeting",
                "slug": "budgeting",
                "description": "Ask questions about budgeting and managing expenses.",
                "display_order": 1,
            },
            {
                "name": "Saving",
                "slug": "saving",
                "description": "Discuss savings habits, emergency funds, and saving goals.",
                "display_order": 2,
            },
            {
                "name": "Debt Management",
                "slug": "debt-management",
                "description": "Discuss loans, repayments, and debt reduction strategies.",
                "display_order": 3,
            },
            {
                "name": "Investing",
                "slug": "investing",
                "description": "Discuss investing basics, risks, and long-term growth.",
                "display_order": 4,
            },
            {
                "name": "Insurance",
                "slug": "insurance",
                "description": "Ask questions about insurance and financial protection.",
                "display_order": 5,
            },
            {
                "name": "Retirement Planning",
                "slug": "retirement-planning",
                "description": "Discuss retirement goals, CPF, and long-term planning.",
                "display_order": 6,
            },
            {
                "name": "Course Help",
                "slug": "course-help",
                "description": "Get help with course materials and platform usage.",
                "display_order": 7,
            },
        ]

        categories = [Category(**item) for item in category_data]
        session.add_all(categories)
        session.flush()

        budgeting_thread = Thread(
            category_id=categories[0].category_id,
            creator_id=None,
            title="How do I start budgeting?",
            slug="how-do-i-start-budgeting",
        )

        saving_thread = Thread(
            category_id=categories[1].category_id,
            creator_id=None,
            title="How can I build a saving habit?",
            slug="how-can-i-build-a-saving-habit",
        )

        investing_thread = Thread(
            category_id=categories[3].category_id,
            creator_id=None,
            title="What is the difference between stocks and ETFs?",
            slug="stocks-vs-etfs",
        )

        session.add_all([budgeting_thread, saving_thread, investing_thread])
        session.flush()

        session.add_all([
            Post(
                thread_id=budgeting_thread.thread_id,
                creator_id=None,
                content="""
                <p>I want to start budgeting but I do not know where to begin.</p>
                <p>What budgeting methods work best for beginners?</p>
                """,
            ),
            Post(
                thread_id=saving_thread.thread_id,
                creator_id=None,
                content="""
                <p>I struggle to save money consistently.</p>
                <p>How can I build a good savings habit?</p>
                """,
            ),
            Post(
                thread_id=investing_thread.thread_id,
                creator_id=None,
                content="""
                <p>I am new to investing.</p>
                <p>What is the difference between stocks and ETFs?</p>
                """,
            ),
        ])
