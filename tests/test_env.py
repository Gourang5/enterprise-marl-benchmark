from enterprise_env.factory import make_env

def test_reset_and_partial_observation():
    e=make_env();o,i=e.reset(seed=42)
    assert i["task_id"]=="customer_incident_v2"
    assert o["agent"]["employee_id"]=="pm_01"
    assert len(o["inbox"])>=1
    assert "body" not in o["inbox"][0]
    assert "subgoals" not in o["task"]
    e.close()

def test_roles_have_different_tools():
    e=make_env();e.reset(seed=1)
    assert "jira.assign_issue" in e.legal_tools("pm_01")
    assert "jira.assign_issue" not in e.legal_tools("eng_01")
    e.close()

def test_seed_same_fixture():
    a=make_env();b=make_env();oa,_=a.reset(42);ob,_=b.reset(42)
    assert oa["inbox"]==ob["inbox"]
    a.close();b.close()
