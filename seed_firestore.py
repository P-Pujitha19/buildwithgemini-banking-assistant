#!/usr/bin/env python3
"""Seed script for Firestore backend collections in Banking Assistant agent."""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-02-40df00ca0376"

CUSTOMERS = {
    "cust_001": {
        "name": "Alex Morgan",
        "email": "alex.morgan@example.com",
        "income": 95000,
        "credit_score": 750,
        "risk_appetite": "moderate",
        "preferred_loan_type": "Home Loan",
        "target_amount": 350000,
        "preferred_tenure_years": 20,
        "status": "active"
    },
    "cust_002": {
        "name": "Jordan Lee",
        "email": "jordan.lee@example.com",
        "income": 65000,
        "credit_score": 680,
        "risk_appetite": "low",
        "preferred_loan_type": "Personal Loan",
        "target_amount": 25000,
        "preferred_tenure_years": 3,
        "status": "active"
    },
    "cust_003": {
        "name": "Sam Taylor",
        "email": "sam.taylor@example.com",
        "income": 120000,
        "credit_score": 810,
        "risk_appetite": "high",
        "preferred_loan_type": "Home Loan",
        "target_amount": 500000,
        "preferred_tenure_years": 15,
        "status": "active"
    }
}

LOANS = {
    "loan_home_fixed": {
        "title": "Standard Fixed-Rate Home Loan",
        "category": "Home Loan",
        "interest_rate_pct": 6.5,
        "min_tenure_years": 5,
        "max_tenure_years": 30,
        "min_amount": 50000,
        "max_amount": 1500000,
        "processing_fee_pct": 0.5,
        "description": "Competitive fixed-rate home mortgage with low processing fees and flexible tenure options."
    },
    "loan_home_flexi": {
        "title": "Flexi-Pay Home Loan",
        "category": "Home Loan",
        "interest_rate_pct": 6.25,
        "min_tenure_years": 10,
        "max_tenure_years": 30,
        "min_amount": 100000,
        "max_amount": 2000000,
        "processing_fee_pct": 0.25,
        "description": "Home loan with interest-only payment option for initial 3 years and zero prepayment penalty."
    },
    "loan_personal_prime": {
        "title": "Prime Personal Loan",
        "category": "Personal Loan",
        "interest_rate_pct": 10.5,
        "min_tenure_years": 1,
        "max_tenure_years": 5,
        "min_amount": 5000,
        "max_amount": 50000,
        "processing_fee_pct": 1.0,
        "description": "Quick approval personal loan for home renovation, travel, or debt consolidation."
    },
    "loan_personal_express": {
        "title": "Express Emergency Personal Loan",
        "category": "Personal Loan",
        "interest_rate_pct": 12.0,
        "min_tenure_years": 1,
        "max_tenure_years": 3,
        "min_amount": 1000,
        "max_amount": 15000,
        "processing_fee_pct": 1.5,
        "description": "Instant disbursement within 2 hours for existing bank customers with pre-approved credit."
    }
}

CREDIT_CARDS = {
    "card_cashback_plus": {
        "title": "Cashback Plus Credit Card",
        "category": "Cashback",
        "annual_fee": 0,
        "apr_pct": 19.99,
        "reward_rate": "3% on groceries & dining, 1% on all other purchases",
        "min_credit_score": 670,
        "features": ["Zero annual fee", "Complimentary roadside assistance", "Contactless pay"]
    },
    "card_travel_rewards": {
        "title": "Global Traveler Sapphire Card",
        "category": "Travel",
        "annual_fee": 95,
        "apr_pct": 18.49,
        "reward_rate": "5x points on travel bookings, 2x on dining",
        "min_credit_score": 740,
        "features": ["Lounge access (4 visits/yr)", "Zero foreign transaction fees", "Travel insurance included"]
    },
    "card_privilege_reserve": {
        "title": "Reserve World Elite Card",
        "category": "Premium",
        "annual_fee": 450,
        "apr_pct": 16.99,
        "reward_rate": "10x points on luxury dining & travel, 3x on all purchases",
        "min_credit_score": 780,
        "features": ["24/7 Concierge service", "Unlimited airport lounge access", "30,000 bonus welcome points"]
    }
}

BANKING_PRODUCTS = {
    "prod_high_yield_savings": {
        "title": "High-Yield Advantage Savings",
        "category": "Savings Account",
        "interest_rate_apy": 4.75,
        "min_balance": 500,
        "monthly_fee": 0,
        "description": "High APY savings account with daily compounded interest and mobile check deposit."
    },
    "prod_wealth_builder_cd": {
        "title": "Wealth Builder 12-Month CD",
        "category": "Certificate of Deposit",
        "interest_rate_apy": 5.25,
        "min_balance": 1000,
        "monthly_fee": 0,
        "description": "Guaranteed return fixed-term certificate of deposit with early withdrawal options."
    },
    "prod_checking_rewards": {
        "title": "Everyday Rewards Checking",
        "category": "Checking Account",
        "interest_rate_apy": 0.50,
        "min_balance": 0,
        "monthly_fee": 0,
        "description": "No fee checking account with free ATM access worldwide and instant card lock."
    }
}


def seed_collection(db: firestore.Client, collection_name: str, records: dict):
    print(f"Seeding collection '{collection_name}'...")
    collection_ref = db.collection(collection_name)
    for doc_id, data in records.items():
        doc_ref = collection_ref.document(doc_id)
        doc_ref.set(data)
        print(f"  - Written document: {doc_id}")


def main():
    print(f"Connecting to Firestore using hardcoded project ID: {PROJECT_ID}")
    db = firestore.Client(project=PROJECT_ID)

    seed_collection(db, "customers", CUSTOMERS)
    seed_collection(db, "loans", LOANS)
    seed_collection(db, "credit_cards", CREDIT_CARDS)
    seed_collection(db, "banking_products", BANKING_PRODUCTS)

    print("\n✅ Firestore seeding completed successfully!")


if __name__ == "__main__":
    main()
