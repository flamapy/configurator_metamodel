"""Shared builders for the configurator_metamodel test suite.

These helpers construct small ``FeatureModel`` fragments by hand so that the
unit tests can exercise specific feature-relation shapes (mandatory, optional,
or-group, alternative-group) without depending on a full UVL file.

They are deliberately tiny and side-effect free: every call returns fresh
objects, so tests never share mutable state.
"""
from flamapy.metamodels.fm_metamodel.models.feature_model import (
    Feature,
    FeatureType,
    Relation,
)


def feature(name: str, feature_type: FeatureType = FeatureType.BOOLEAN) -> Feature:
    """Create a standalone feature with no relations."""
    return Feature(name, feature_type=feature_type)


def mandatory(parent: Feature, child: Feature) -> None:
    """Attach *child* to *parent* as a mandatory relation [1, 1]."""
    parent.add_relation(Relation(parent, [child], 1, 1))


def optional(parent: Feature, child: Feature) -> None:
    """Attach *child* to *parent* as an optional relation [0, 1]."""
    parent.add_relation(Relation(parent, [child], 0, 1))


def alternative(parent: Feature, children: list[Feature]) -> None:
    """Attach *children* to *parent* as an alternative group [1, 1]."""
    parent.add_relation(Relation(parent, children, 1, 1))


def or_group(parent: Feature, children: list[Feature]) -> None:
    """Attach *children* to *parent* as an or group [1, n]."""
    parent.add_relation(Relation(parent, children, 1, len(children)))
