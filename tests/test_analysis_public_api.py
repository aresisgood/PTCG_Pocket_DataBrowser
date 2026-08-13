"""The package facade exposes runtime values without eager ML imports."""

import subprocess
import sys


def test_importing_analysis_does_not_eagerly_import_sklearn():
    result = subprocess.run(
        [sys.executable, "-c",
         "import analysis, sys; assert 'sklearn' not in sys.modules"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_offline_builder_and_trainer_remain_public_lazy_exports():
    from analysis import ModelArtifactError, build_analysis, train_model

    assert callable(build_analysis)
    assert callable(train_model)
    assert issubclass(ModelArtifactError, RuntimeError)
