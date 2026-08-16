from .env import EnterpriseEnv
from .config import EnvConfig
from .tasks.factory import make_task

def make_task(name):return __import__("enterprise_env.tasks.factory",fromlist=["make_task"]).make_task(name)
def make_env(task_name="customer_incident",max_steps=None):
    t=make_task(task_name);return EnterpriseEnv(t,EnvConfig(max_steps=max_steps or t.max_steps))
