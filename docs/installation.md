# Installing Airless

## Using uv

### Create uv environment
We recommend creating an uv environment first:

```bash
uv init --bare --no-workspace
```

### Install airless-core
Now, add airless-core to your environment, that is the main package:

```bash
uv add airless-core
```

## Using pip and venv

### Create & activate virtual environment
We recommend creating a virtual Python environment using venv:

```bash
python -m venv .venv
```

Now, you can activate the virtual environment using the appropriate command for your operating system and environment:

```text
# Mac / Linux
source .venv/bin/activate

# Windows CMD:
.venv\Scripts\activate.bat

# Windows PowerShell:
.venv\Scripts\Activate.ps1
```

### Install airless-core

```bash
pip install airless-core
```

## Next Steps

Try creating your first workflow with the [Quickstart](tutorials/quickstart.md).