from enterprise_env.factory import make_env
env=make_env();env.reset(seed=42)
print("Employees:")
for e in env.repo.employees():print(e)
print("\nAgent legal tools:")
for a in env.AGENTS:print(a,env.legal_tools(a))
env.close()
