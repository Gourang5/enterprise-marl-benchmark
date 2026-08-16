from enterprise_env.database import CompanyRepository,seed_company

def test_five_consistent_people():
    r=seed_company(CompanyRepository());assert len(r.employees())==5;assert r.employee("eng_01")["name"]=="Arjun";r.close()
def test_foreign_keys():
    r=seed_company(CompanyRepository());assert r.conn.execute("PRAGMA foreign_keys").fetchone()[0]==1;r.close()


def test_enterprise_search_handles_natural_language_query_terms():
    from enterprise_env.factory import make_env
    env = make_env("customer_incident")
    env.reset(seed=100)
    try:
        emails = env.repo.search_emails("pm_01", "authentication outage")
        issues = env.repo.search_issues("production authentication outage")
        assert emails and emails[0]["email_id"] == "seed-email-001"
        assert issues and issues[0]["issue_id"] == "INC-421"
    finally:
        env.close()
