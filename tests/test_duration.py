import random

import pytest

from b2b_workflow_simulator.primitives.duration import DurationModel


def test_fixed_duration_ignores_randomness():
    model = DurationModel()
    rng = random.Random(1)

    for _ in range(5):
        assert model.sample(rng, 10.0) == 10.0


def test_uniform_duration_respects_explicit_bounds():
    model = DurationModel(kind="uniform", minimum=5.0, maximum=15.0)
    rng = random.Random(1)

    samples = [model.sample(rng, 10.0) for _ in range(200)]

    assert all(5.0 <= sample <= 15.0 for sample in samples)


def test_uniform_duration_defaults_bounds_from_base():
    model = DurationModel(kind="uniform")
    rng = random.Random(1)

    samples = [model.sample(rng, 100.0) for _ in range(200)]

    assert all(80.0 <= sample <= 120.0 for sample in samples)


def test_triangular_duration_respects_explicit_bounds():
    model = DurationModel(kind="triangular", minimum=5.0, mode=10.0, maximum=20.0)
    rng = random.Random(1)

    samples = [model.sample(rng, 10.0) for _ in range(200)]

    assert all(5.0 <= sample <= 20.0 for sample in samples)


def test_triangular_duration_defaults_mode_to_base():
    model = DurationModel(kind="triangular", minimum=5.0, maximum=15.0)
    rng = random.Random(1)

    samples = [model.sample(rng, 10.0) for _ in range(500)]
    average = sum(samples) / len(samples)

    # With mode == base (10.0), the distribution is symmetric around 10.
    assert 9.0 < average < 11.0


def test_sampling_is_deterministic_given_the_same_seed():
    model = DurationModel(kind="triangular", minimum=5.0, mode=10.0, maximum=20.0)

    rng_a = random.Random(42)
    rng_b = random.Random(42)

    samples_a = [model.sample(rng_a, 10.0) for _ in range(20)]
    samples_b = [model.sample(rng_b, 10.0) for _ in range(20)]

    assert samples_a == samples_b


def test_different_seeds_produce_different_samples():
    model = DurationModel(kind="uniform", minimum=0.0, maximum=100.0)

    samples_a = [model.sample(random.Random(1), 10.0) for _ in range(20)]
    samples_b = [model.sample(random.Random(2), 10.0) for _ in range(20)]

    assert samples_a != samples_b


def test_rejects_unknown_kind():
    with pytest.raises(ValueError, match="kind"):
        DurationModel(kind="exponential")


def test_rejects_negative_minimum():
    with pytest.raises(ValueError, match="minimum"):
        DurationModel(kind="uniform", minimum=-1.0)


def test_rejects_minimum_greater_than_maximum():
    with pytest.raises(ValueError, match="minimum"):
        DurationModel(kind="uniform", minimum=20.0, maximum=10.0)
