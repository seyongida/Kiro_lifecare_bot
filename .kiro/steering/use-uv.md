---
inclusion: always
---

# Python Execution with uv

When running Python code, ALWAYS use `uv` instead of creating virtual environments manually.

## Rules

- **NEVER** create venv with `python3 -m venv venv`
- **NEVER** use `source venv/bin/activate`
- **NEVER** use `pip install` or `pip3 install`
- **NEVER** use `uv run python3 -c "..."` with multi-line code — it causes shell quoting issues (`dquote>` hang)

## Use uv Instead

For simple one-liners only:

```bash
uv run python3 -c "print('hello')"
```

For running Python scripts:

```bash
uv run python3 script.py
```

For multi-line code, ALWAYS write to a temporary script file, execute it, then delete it:

```bash
# 1. Write code to a temp file
# 2. Run it: uv run python3 _tmp_script.py
# 3. Delete it after execution: rm _tmp_script.py
```

For specifying dependencies inline:

```bash
uv run --with pillow --with requests python3 script.py
```

## Benefits

- No manual venv creation/activation needed
- Automatic dependency management
- Faster and cleaner workflow
- Dependencies are isolated per execution