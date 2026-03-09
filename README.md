# configurator_metamodel

[![CI](https://github.com/flamapy/configurator_metamodel/actions/workflows/lint.yml/badge.svg)](https://github.com/flamapy/configurator_metamodel/actions)
[![PyPI](https://img.shields.io/pypi/v/flamapy-configurator)](https://pypi.org/project/flamapy-configurator/)
[![Python](https://img.shields.io/pypi/pyversions/flamapy-configurator)](https://pypi.org/project/flamapy-configurator/)
[![License](https://img.shields.io/github/license/flamapy/configurator_metamodel)](LICENSE)

A [Flamapy](https://flamapy.github.io/) plugin that transforms a Feature Model into an
interactive configurator.  It guides users through a sequence of questions—one per
feature group—and uses a solver to reject inconsistent selections in real time.

## Features

- Loads Feature Models in **UVL** format via `flamapy-fm`
- Converts the FM into an ordered list of **questions** and **options**
- **Two interchangeable solver backends** — choose based on your model:
  - **PySAT / Glucose3** (default) — fast SAT-based unit propagation for boolean models
  - **Z3 SMT solver** — full support for typed features (`INTEGER`, `REAL`, `STRING`) and arithmetic cross-tree constraints
- Full **undo** support: revert the last answer at any point
- Exposes a clean dictionary-based API suitable for embedding in web or CLI apps

## Installation

```bash
pip install flamapy-configurator
```

For typed-feature models (INTEGER, REAL, STRING), also install the Z3 extra:

```bash
pip install "flamapy-configurator[z3]"
```

Or install from source:

```bash
git clone https://github.com/flamapy/configurator_metamodel
cd configurator_metamodel
pip install -e .           # PySAT backend only
pip install -e ".[z3]"     # PySAT + Z3 backends
```

### Requirements

| Package | Version | Required |
|---------|---------|---------|
| `flamapy-fw` | ~2.5.0 | always |
| `flamapy-fm` | ~2.5.0 | always |
| `flamapy-sat` | ~2.5.0 | always |
| `flamapy-z3` | ~2.5.0 | only for Z3 backend |
| Python | ≥ 3.9 | always |

## Choosing a solver backend

Pass `solver='pysat'` (default) or `solver='z3'` to `FmToConfigurator`:

| Scenario | Recommended backend |
|----------|-------------------|
| Pure boolean feature model | `pysat` (faster) |
| Model with `Integer` / `Real` / `String` features | `z3` |
| Arithmetic cross-tree constraints (`price > 10`, `qty >= 2`) | `z3` |

```python
from flamapy.metamodels.configurator_metamodel.transformation.fm_to_configurator import FmToConfigurator

# Boolean model — PySAT (default)
configurator_model = FmToConfigurator(fm).transform()

# Typed-feature model — Z3
configurator_model = FmToConfigurator(fm, solver='z3').transform()
```

### How each backend propagates constraints

After each answer the backend checks whether the current partial configuration
is still satisfiable and derives any additionally forced feature values:

- **PySAT** runs *unit propagation* on the CNF encoding of the feature model.
  This is very fast (linear in the number of clauses) but operates only on
  boolean selection — typed values are not propagated.

- **Z3** calls `solver.check()` with the current decisions as assumptions, then
  performs *backbone detection*: for every undecided feature it checks whether
  fixing it in either direction would be UNSAT.  This is slower (one SMT call
  per undecided feature) but handles arbitrary arithmetic constraints natively.

## Quick start

```python
from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.configurator_metamodel.transformation.fm_to_configurator import FmToConfigurator
from flamapy.metamodels.configurator_metamodel.operations.configure import Configure

# 1. Load a feature model
fm = UVLReader('model.uvl').transform()

# 2. Build the configurator model — use solver='z3' for typed features
configurator_model = FmToConfigurator(fm).transform()

# 3. Create and start the configure operation
op = Configure()
op.execute(configurator_model)
op.start()

# 4. Iterate through questions
while not op.is_finished():
    status = op.get_current_status()
    print(f"\nQuestion: {status['currentQuestion']} ({status['currentQuestionType']})")

    for opt in status['possibleOptions']:
        print(f"  [{opt['id']}] {opt['name']}  (type: {opt['featureType']})")

    # Answer with a dict {option_name: value}
    # Value type must match the feature type: bool, int, float, or str
    choice_name = status['possibleOptions'][0]['name']
    success = op.answer_question({choice_name: True})

    if not success:
        print("Contradiction! Try a different option.")
        continue

    if not op.next_question():
        break  # No more questions

print("Configuration complete!")
```

### Typed-feature example (Z3 backend)

```python
# model.uvl contains: Integer SpicyLevel, with constraint SpicyLevel >= 1 & SpicyLevel <= 5
fm = UVLReader('model.uvl').transform()
configurator_model = FmToConfigurator(fm, solver='z3').transform()

op = Configure()
op.execute(configurator_model)
op.start()

while not op.is_finished():
    status = op.get_current_status()
    for opt in status['possibleOptions']:
        feature_type = opt['featureType'].name  # 'BOOLEAN', 'INTEGER', 'REAL', 'STRING'
        if feature_type == 'INTEGER':
            op.answer_question({opt['name']: 3})
        elif feature_type == 'REAL':
            op.answer_question({opt['name']: 9.99})
        elif feature_type == 'STRING':
            op.answer_question({opt['name']: 'Margherita'})
        else:
            op.answer_question({opt['name']: True})
    op.next_question()
```

## API reference

### `FmToConfigurator(source_model, solver='pysat')`

Transforms a `FeatureModel` into a `ConfiguratorModel`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `source_model` | `FeatureModel` | The feature model to configure. |
| `solver` | `str` | Backend to use: `'pysat'` (default) or `'z3'`. |

| Method | Description |
|--------|-------------|
| `transform()` | Run the transformation and return the `ConfiguratorModel`. |

### `Configure`

The main operation class.  Call `execute(model)` to initialise.

| Method | Returns | Description |
|--------|---------|-------------|
| `start()` | `None` | Advance to the first question. |
| `get_current_status()` | `dict` | Status snapshot (question name, type, options, …). |
| `answer_question(answer)` | `bool` | Apply `{name: value}` dict; returns `False` on conflict. |
| `next_question()` | `bool` | Move to the next question; `False` when finished. |
| `previous_question()` | `bool` | Move to the previous question; `False` when at the start. |
| `undo_answer()` | `bool` | Revert to the state before the last answer. |
| `is_finished()` | `bool` | `True` when all questions have been answered. |
| `get_result()` | `dict` | Current configuration as `{feature_name: value}`. |

## Running the tests

```bash
make test        # pytest tests/ -sv
make cov         # coverage report + html
```

## License

GPLv3+.  See [LICENSE](LICENSE) for details.
