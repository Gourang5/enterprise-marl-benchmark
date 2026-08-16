# Reward Design

Reward is based on task progress, coordination, action validity and final outcome—not on the number of apps used.

Starting formula:
R = valid_action + progress_reward + coordination_bonus + terminal_success + step_cost - penalties

Run an ablation between shaped reward and sparse terminal reward. Watch for reward hacking such as repeated reads/messages, premature status changes or irrelevant tool use.
