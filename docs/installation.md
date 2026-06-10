# Installation

## Python Requirements

Blocklog requires **Python 3.11** or newer.
You also need the following dependencies which are automatically installed:
- `httpx` (>=0.27, <1.0)
- `pydantic` (>=2.8, <3.0)

## Installation from GitHub

You can install the SDK directly from the GitHub repository using `pip`:

```bash
pip install git+https://github.com/blockloghq/blocklog-python.git
```

## Development Installation

If you want to contribute to the SDK or run the examples locally, clone the repository and install it in editable mode:

```bash
git clone https://github.com/blockloghq/blocklog-python.git
cd blocklog-python
pip install -e .
```

## Verification

To verify that the installation was successful, open a Python shell and try to import `blocklog`:

```python
import blocklog
print(blocklog.__version__)
# Expected output: 0.2.0
```
