# Running the Enterprise MARL Benchmark on Windows (VS Code)

All commands below run in the **VS Code integrated terminal** (PowerShell).  
Open VS Code → `Ctrl+`` ` (backtick) to open the terminal.

---

## Step 1 — One-time setup

```powershell
cd "C:\Users\Shubham\OneDrive - Indian Institute of Technology Guwahati\Desktop\enterprise-marl-research-grade-v1.2\enterprise-marl-improved"
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Verify everything works (should show **118 passed**):

```powershell
pytest -q
```

---

## Step 2 — Run the deterministic demo (no LLM key needed)

```powershell
python examples/customer_incident_demo.py
python scripts/compare_baselines.py --episodes 25
```

---

## Step 3 — Run the LLM benchmark (choose ONE free provider)

### Option A — Google Gemini (FREE, recommended)

1. Go to **https://aistudio.google.com/app/apikey** → sign in with Google → "Create API key"
2. In VS Code terminal:

```powershell
$env:GEMINI_API_KEY = "AIza..."   # paste your key here

# Single task, one episode
python scripts/run_llm_benchmark.py --provider gemini --task customer_incident --episodes 1

# All six tasks
python scripts/run_llm_benchmark.py --provider gemini --task all --episodes 1

# Stronger model (still free up to usage limits)
python scripts/run_llm_benchmark.py --provider gemini --model gemini-2.5-flash --task all --episodes 3
```

Results are saved in `benchmark_results/llm_results.json` and `.csv`.

---

### Option B — Alibaba Qwen via DashScope (FREE)

1. Go to **https://dashscope.aliyuncs.com** → "Register" with email/Alibaba Cloud
2. Dashboard → API Keys → Create key

```powershell
$env:DASHSCOPE_API_KEY = "sk-..."   # paste your key here

python scripts/run_llm_benchmark.py --provider qwen --task customer_incident --episodes 1
python scripts/run_llm_benchmark.py --provider qwen --task all --episodes 3

# Stronger model
python scripts/run_llm_benchmark.py --provider qwen --model qwen-plus --task all --episodes 3
```

---

### Option C — Groq Cloud (FREE, fastest)

1. Go to **https://console.groq.com** → sign in with GitHub or Google → "Create API key"

```powershell
$env:GROQ_API_KEY = "gsk_..."   # paste your key here

python scripts/run_llm_benchmark.py --provider groq --task customer_incident --episodes 1
python scripts/run_llm_benchmark.py --provider groq --task all --episodes 3

# Stronger model
python scripts/run_llm_benchmark.py --provider groq --model llama-3.3-70b-versatile --task all --episodes 3
```

---

### Option D — Ollama (local, NO key, but slow ~10 s/call on CPU)

```powershell
# Install Ollama from https://ollama.com then in a new terminal:
ollama pull qwen2.5:7b

# Back in the project terminal:
python scripts/run_llm_benchmark.py --provider ollama --model qwen2.5:7b --task customer_incident --episodes 1
```

---

## Step 4 — Centralized vs Decentralized comparison

```powershell
python scripts/run_llm_benchmark.py --provider gemini --task all --episodes 3 --mode centralized  --output benchmark_results/gemini_centralized.json
python scripts/run_llm_benchmark.py --provider gemini --task all --episodes 3 --mode decentralized --output benchmark_results/gemini_decentralized.json
```

---

## Step 5 — Trajectory export and visual viewer

```powershell
python scripts/export_trajectory.py --task customer_incident --seed 42
pip install -e ".[ui]"
streamlit run ui/app.py
```

Open http://localhost:8501 in your browser.

---

## Step 6 — Other useful commands

```powershell
# Inspect the seeded company state
python scripts/inspect_company.py

# Diagnose Ollama connectivity (if using Ollama)
python scripts/diagnose.py --model qwen2.5:7b

# Run reward ablation
python scripts/run_reward_ablation.py

# Generate train/dev/test scenario dataset
python scripts/generate_dataset.py --output generated_scenarios --train 100 --dev 20 --test 50

# Run all tests
pytest -v
```

---

## Provider comparison at a glance

| Provider   | Key needed | Speed      | Quality  | Sign-up URL                              |
|------------|------------|------------|----------|------------------------------------------|
| **gemini** | Yes (FREE) | ~1–2 s/call | ★★★★☆  | https://aistudio.google.com/app/apikey  |
| **qwen**   | Yes (FREE) | ~1–2 s/call | ★★★★☆  | https://dashscope.aliyuncs.com           |
| **groq**   | Yes (FREE) | <1 s/call  | ★★★★☆  | https://console.groq.com                |
| ollama     | No         | ~10 s/call | ★★★☆☆  | https://ollama.com                       |
| anthropic  | Yes (paid) | ~1 s/call  | ★★★★★  | https://console.anthropic.com            |
