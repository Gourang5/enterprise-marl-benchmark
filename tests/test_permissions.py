from enterprise_env.core.actions import Action
from enterprise_env.factory import make_env

def test_unauthorized_action_gets_negative_reward():
    e=make_env();e.reset(1)
    _,r,_,_,info=e.step(Action("eng_01","jira","assign_issue",{"issue_id":"INC-421","assignee_id":"eng_01"}))
    assert r<0 and not info["success"]
    e.close()
