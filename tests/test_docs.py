"""Check that docs/SCORING.md still quotes the constants the code uses.

Documentation that lists numbers goes stale silently: someone retunes a
burial value, the tests still pass, and the doc now lies. Worse, writing
the doc is itself error-prone - the first draft of SCORING.md quoted a
Val/Val burial of -0.44 when the real figure at an 'a' position is -1.20,
and nothing would have caught it.

So the doc is treated as an assertion about the code. If you change a
constant, this fails until the doc is updated to match.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from lz import params as P
from lz import scoring as S
from lz.orthogonal import DEFAULT_CROSS_MARGIN
from lz.structure import AMBIGUOUS_FIT, AMBIGUOUS_MARGIN, IDEAL_PROFILE

DOC = Path(__file__).resolve().parent.parent / "docs" / "SCORING.md"


@pytest.fixture(scope="module")
def text() -> str:
    if not DOC.exists():
        pytest.fail(f"{DOC} is missing")
    # The doc uses the typographic minus sign U+2212 in prose.
    return io.open(DOC, encoding="utf-8").read().replace("\u2212", "-")


@pytest.mark.parametrize("position", ["a", "d"])
def test_burial_table_is_current(text, position):
    for residue, value in P.BURIAL[position].items():
        assert f"{residue} {value:+.2f}" in text, (position, residue, value)


def test_pair_bonuses_are_current(text):
    for (position, pair), value in P.PAIR_BONUS.items():
        assert f"{value:+.2f}" in text, (position, sorted(pair), value)


def test_helix_propensity_table_is_current(text):
    for residue, value in P.HELIX_PROPENSITY.items():
        assert f"{residue} {value:.2f}" in text, (residue, value)


def test_ideal_heptad_profile_is_current(text):
    for position, value in IDEAL_PROFILE.items():
        assert f"{value:+.3f}" in text, (position, value)


@pytest.mark.parametrize(
    "label,value,fmt",
    [
        ("IDEAL_LAYER_VOLUME", P.IDEAL_LAYER_VOLUME, "{:.1f}"),
        ("VOLUME_PENALTY", P.VOLUME_PENALTY, "{:.3f}"),
        ("UNSATISFIED_POLAR", P.UNSATISFIED_POLAR, "{:.2f}"),
        ("BURIED_LIKE_CHARGE", P.BURIED_LIKE_CHARGE, "{:.2f}"),
        ("SALT_BRIDGE_ATTRACT", abs(P.SALT_BRIDGE_ATTRACT), "{:.2f}"),
        ("SALT_BRIDGE_REPEL", P.SALT_BRIDGE_REPEL, "{:.2f}"),
        ("POLAR_CHARGE_CONTACT", abs(P.POLAR_CHARGE_CONTACT), "{:.2f}"),
        ("SPECIFICITY_MARGIN", P.SPECIFICITY_MARGIN, "{:.1f}"),
        ("DEFAULT_CROSS_MARGIN", DEFAULT_CROSS_MARGIN, "{:.1f}"),
        ("MIN_OVERLAP_LAYERS", S.MIN_OVERLAP_LAYERS, "{:d}"),
        ("MAX_SLIP_HEPTADS", S.MAX_SLIP_HEPTADS, "{:d}"),
        ("AMBIGUOUS_FIT", AMBIGUOUS_FIT, "{:.2f}"),
        ("AMBIGUOUS_MARGIN", AMBIGUOUS_MARGIN, "{:.2f}"),
        ("TM_INTERCEPT", P.TM_INTERCEPT, "{:.1f}"),
    ],
)
def test_scalar_constants_are_current(text, label, value, fmt):
    assert fmt.format(value) in text, label


@pytest.mark.parametrize("term", ["core", "electrostatic", "helix"])
def test_model_weights_are_current(text, term):
    assert f"{P.DEFAULT_WEIGHTS[term]:.1f}" in text, term


def test_worked_example_matches_the_scorer(text):
    """The GCN4 homodimer figures printed in the doc must be reproducible."""
    gcn4 = "RMKQLEDKVEELLSKNYHLENEVARLKKLVGER"
    score = S.score_pair(gcn4, gcn4)
    for label, value in [
        ("total", score.total),
        ("core", score.core),
        ("electro", score.electrostatic),
        ("helix", score.helix),
    ]:
        assert f"{value:+.2f}" in text, (label, value)
    assert f"layers     {score.n_layers} (heptad shift {score.shift:+d})" in text


@pytest.mark.parametrize(
    "position,r1,r2",
    [("d", "L", "L"), ("d", "R", "R"), ("a", "N", "N"), ("a", "V", "V")],
)
def test_layer_energies_quoted_in_the_example_are_current(text, position, r1, r2):
    energy = S.core_layer_energy(position, r1, r2)
    assert f"{r1}-{r2}  {energy:+.2f}" in text, (position, r1, r2, energy)


def test_the_doc_states_the_scores_are_not_energies(text):
    """The single most important caveat must not be edited away."""
    assert "순위이지 에너지가 아닙니다" in text
    assert "피팅되지 않았습니다" in text
