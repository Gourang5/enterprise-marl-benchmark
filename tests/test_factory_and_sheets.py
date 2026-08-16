from enterprise_env.factory import make_env
from enterprise_env.evaluation.runner import run_episode
from enterprise_env.generation import ScenarioFactory
from enterprise_env.core.actions import Action


def test_launch_readiness_baseline_completes():
    r = run_episode("launch_readiness", seed=7)
    assert r["success"] is True
    assert r["progress"] == 1.0
    assert r["steps"] <= 45


def test_sheets_enforce_membership_role():
    env = make_env("launch_readiness")
    env.reset(seed=1)
    _, _, _, _, info = env.step(Action("cs_01", "sheets", "update_cell", {"sheet_id":"SHEET-LAUNCH","cell":"B2","value":"READY"}))
    assert info["success"] is False
    assert "read-only" in info["message"].lower()
    env.close()


def test_factory_split_is_disjoint_and_reproducible(tmp_path):
    f = ScenarioFactory()
    a = f.generate_split(n=8, split="train", difficulty="hard", seed=11)
    b = f.generate_split(n=8, split="train", difficulty="hard", seed=11)
    c = f.generate_split(n=8, split="test", difficulty="hard", seed=11)
    assert a == b
    assert {x["seed"] for x in a}.isdisjoint({x["seed"] for x in c})
    manifest = f.export_dataset(tmp_path, train=4, dev=2, test=3, seed=2)
    assert manifest["splits"]["test"]["episodes"] == 3
    assert (tmp_path / "manifest.json").exists()


def test_factory_adversarial_adds_distractors():
    env, _, info = ScenarioFactory().build("meeting_conflict", seed=3, difficulty="adversarial")
    assert info["distractors"] == 30
    assert len(env.repo.all("SELECT * FROM emails WHERE email_id LIKE 'factory-noise-%'")) == 30
    env.close()
