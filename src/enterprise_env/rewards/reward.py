class RewardEngine:
    def __init__(self,verifier,cfg):
        self.verifier,self.cfg=verifier,cfg;self.prev=0.0
    def reset(self): self.prev=0.0
    def compute(self,repo,result,terminated,truncated):
        if not result.success:
            return self.cfg.invalid_action,{"invalid":self.cfg.invalid_action}
        p=self.verifier.progress(repo); delta=max(0,p-self.prev)
        # Successful no-op/read loops cost reward instead of farming it.
        base=self.cfg.valid_action if (result.changed or result.informative or delta>0) else self.cfg.redundant_action
        r=base+self.cfg.progress_per_full_subgoal*delta+self.cfg.step_cost
        comp={"useful_or_redundant":base,"progress":self.cfg.progress_per_full_subgoal*delta,"coordination":0.0,"terminal":0.0,"step_cost":self.cfg.step_cost}
        if result.coordination and (result.changed or result.informative or delta>0): r+=self.cfg.coordination_bonus;comp["coordination"]=self.cfg.coordination_bonus
        if terminated:r+=self.cfg.terminal_success;comp["terminal"]=self.cfg.terminal_success
        if truncated:r+=self.cfg.timeout;comp["timeout"]=self.cfg.timeout
        self.prev=p;return r,comp
