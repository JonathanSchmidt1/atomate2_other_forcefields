import pytest

from atomate2.vasp.flows.mp import MPMetaGGARelax
from atomate2.vasp.jobs.mp import (
    MPMetaGGARelaxMaker,
    MPPreRelaxMaker,
)

expected_incar = {
    "ISIF": 3,
    "IBRION": 2,
    "NSW": 99,
    "ISMEAR": 0,
    "SIGMA": 0.05,
    "LREAL": False,
    "LWAVE": False,
    "LCHARG": True,
    "EDIFF": 1e-05,
    "EDIFFG": -0.02,
    "GGA": "PS",
}


def test_mp_pre_relax_maker_default_values():
    maker = MPPreRelaxMaker()
    assert maker.name == "MP pre-relax"
    assert {*maker.input_set_generator.config_dict} >= {"INCAR", "KPOINTS", "POTCAR"}
    for key, expected in expected_incar.items():
        actual = maker.input_set_generator.config_dict["INCAR"][key]
        assert actual == expected, f"{key=}, {actual=}, {expected=}"


def test_mp_relax_maker_default_values():
    maker = MPMetaGGARelaxMaker()
    assert maker.name == "MP meta-GGA Relax"
    assert {*maker.input_set_generator.config_dict} >= {"INCAR", "KPOINTS", "POTCAR"}
    for key, expected in expected_incar.items():
        actual = maker.input_set_generator.config_dict["INCAR"][key]
        assert actual == expected, f"{key=}, {actual=}, {expected=}"


@pytest.mark.parametrize(
    "initial_static_maker, final_relax_maker",
    [
        (MPPreRelaxMaker(), MPMetaGGARelaxMaker()),
        (MPPreRelaxMaker(), None),
        (None, MPMetaGGARelaxMaker()),
        (None, None),  # test it doesn't raise without optional makers
    ],
)
def test_mp_meta_gga_relax_default_values(initial_static_maker, final_relax_maker):
    job = MPMetaGGARelax(
        initial_maker=initial_static_maker, final_relax_maker=final_relax_maker
    )
    assert isinstance(job.initial_maker, type(initial_static_maker))
    if initial_static_maker:
        assert job.initial_maker.name == "MP pre-relax"

    assert isinstance(job.final_relax_maker, type(final_relax_maker))
    if final_relax_maker:
        assert job.final_relax_maker.name == "MP meta-GGA Relax"

    assert job.name == "MP Meta-GGA Relax"


def test_mp_meta_gga_relax_custom_values():
    initial_maker = MPPreRelaxMaker()
    final_relax_maker = MPMetaGGARelaxMaker()
    job = MPMetaGGARelax(
        name="Test",
        initial_maker=initial_maker,
        final_relax_maker=final_relax_maker,
    )
    assert job.name == "Test"
    assert job.initial_maker == initial_maker
    assert job.final_relax_maker == final_relax_maker


def test_mp_relax(mock_vasp, clean_dir, si_structure):
    from emmet.core.tasks import TaskDoc
    from jobflow import run_locally

    # mapping from job name to directory containing test files
    ref_paths = {"relax": "Si_mp_relax/relax"}

    # settings passed to fake_run_vasp; adjust these to check for certain INCAR settings
    fake_run_vasp_kwargs = {
        "relax": {"incar_settings": ["EDIFFG", "METAGGA", "GGA"]},
    }

    # automatically use fake VASP and write POTCAR.spec during the test
    mock_vasp(ref_paths, fake_run_vasp_kwargs)

    # generate flow
    job = MPMetaGGARelaxMaker().make(si_structure)

    # Run the flow or job and ensure that it finished running successfully
    responses = run_locally(job, create_folders=True, ensure_success=True)

    # validate output
    output = responses[job.jobs[0].uuid][1].output

    assert isinstance(output, TaskDoc)
    assert output.output.energy == pytest.approx(-10.85043620)

    # # Now try with a custom maker
    ref_paths = {"relax": "Si_mp_relax_custom/relax"}
    mock_vasp(ref_paths, fake_run_vasp_kwargs)
    custom_maker = MPMetaGGARelaxMaker(
        input_set_generator=MPMetaGGARelaxMaker(
            user_incar_settings={"EDIFFG": -0.05, "METAGGA": None, "GGA": "PS"}
        )
    )
    job = MPMetaGGARelaxMaker(relax_maker2=custom_maker).make(si_structure)
    run_locally(job, create_folders=True, ensure_success=True)
