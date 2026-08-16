FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace
COPY pyproject.toml requirements.txt README.md ./
COPY src ./src
COPY configs ./configs
COPY tasks ./tasks
COPY scripts ./scripts
COPY examples ./examples
COPY tests ./tests
COPY docs ./docs
COPY deliverables ./deliverables
COPY ui ./ui
RUN pip install --no-cache-dir -e '.[dev]' && pip install --no-cache-dir streamlit>=1.36
CMD ["python", "scripts/diagnose.py", "--skip-ollama"]
