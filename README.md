# configurator_metamodel

A [Flamapy](https://flamapy.github.io/) plugin that transforms a Feature Model into an
interactive configurator.  It guides users through a sequence of questions—one per
feature group—and uses a SAT solver to reject inconsistent selections in real time.

## Features

- Loads Feature Models in **UVL** format via `flamapy-fm`
- Converts the FM into an ordered list of **questions** and **options**
- Propagates constraints after every answer using **PySAT / Glucose3**
- Supports **typed features**: `BOOLEAN`, `INTEGER`, `REAL`, `STRING`
- Full **undo** support: revert the last answer at any point
- Exposes a clean dictionary-based API suitable for embedding in web or CLI apps

## Installation

```bash
pip install flamapy-configurator
```

Or install from source:

```bash
git clone https://github.com/flamapy/configurator_metamodel
cd configurator_metamodel
pip install -e .
```

### Requirements

| Package | Version |
|---------|---------|
| `flamapy-fw` | ~2.0.1 |
| `flamapy-fm` | ~2.0.0 |
| `flamapy-pysat` | see `requirements.txt` |
| Python | ≥ 3.9 |

## Quick start

```python
from flamapy.metamodels.fm_metamodel.transformations import UVLReader
from flamapy.metamodels.configurator_metamodel.transformation.fm_to_configurator import FmToConfigurator
from flamapy.metamodels.configurator_metamodel.operations.configure import Configure

# 1. Load a feature model
fm = UVLReader('model.uvl').transform()

# 2. Build the configurator model
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
    choice_name = status['possibleOptions'][0]['name']
    success = op.answer_question({choice_name: True})

    if not success:
        print("Contradiction! Try a different option.")
        continue

    if not op.next_question():
        break  # No more questions

print("Configuration complete!")
```

## API reference

### `FmToConfigurator(source_model)`

Transforms a `FeatureModel` into a `ConfiguratorModel`.

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

## Running the tests

```bash
python -m pytest verify_refactor.py -v
```

## License

GPLv3+.  See [LICENSE](LICENSE) for details.
