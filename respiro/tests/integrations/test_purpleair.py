from respiro.integrations.purpleair import apply_epa_correction


def test_apply_epa_correction_bounds():
    corrected = apply_epa_correction(50, 80)
    assert corrected >= 0
    higher = apply_epa_correction(150, 30)
    assert higher > corrected

