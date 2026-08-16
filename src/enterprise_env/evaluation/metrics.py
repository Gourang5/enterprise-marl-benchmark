from __future__ import annotations
import math

def _mean(xs): return sum(xs) / len(xs) if xs else 0.0

def _std(xs):
    if len(xs) < 2: return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x-m)**2 for x in xs) / (len(xs)-1))

def _wilson(successes:int,n:int,z:float=1.96):
    if n == 0:return [0.0,0.0]
    p=successes/n; den=1+z*z/n
    centre=(p+z*z/(2*n))/den
    margin=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return [max(0.0,centre-margin),min(1.0,centre+margin)]

def aggregate(results):
    if not results:return {}
    n=len(results); rewards=[float(x["reward"]) for x in results]; steps=[float(x["steps"]) for x in results]; successes=[bool(x["success"]) for x in results]
    success_count=sum(successes); llm_calls=sum((x.get("llm") or {}).get("calls",0) for x in results)
    return {
        "episodes":n,"success_rate":success_count/n,"success_count":success_count,"success_rate_95ci":_wilson(success_count,n),
        "avg_reward":_mean(rewards),"reward_std":_std(rewards),"avg_steps":_mean(steps),"steps_std":_std(steps),
        "avg_steps_on_success":_mean([float(x["steps"]) for x in results if x["success"]]),
        "avg_progress":_mean([float(x["progress"]) for x in results]),"timeout_rate":_mean([bool(x["truncated"]) for x in results]),
        "policy_error_rate":_mean([bool(x.get("policy_error")) for x in results]),
        "avg_invalid_action_rate":_mean([float(x.get("invalid_action_rate",0.0)) for x in results]),
        "avg_repeated_actions":_mean([float(x.get("repeated_actions",0.0)) for x in results]),
        "avg_permission_violations":_mean([float(x.get("permission_violations",0.0)) for x in results]),
        "avg_constraint_violations":_mean([float(x.get("constraint_violations",0.0)) for x in results]),
        "llm_calls":llm_calls,"prompt_tokens":sum((x.get("llm") or {}).get("prompt_tokens",0) for x in results),
        "completion_tokens":sum((x.get("llm") or {}).get("completion_tokens",0) for x in results),
        "llm_latency_s":sum((x.get("llm") or {}).get("latency_s",0.0) for x in results),
    }
