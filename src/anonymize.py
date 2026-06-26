"""Create anonymized app-facing data files.

The modeling pipeline keeps `id_student` for group splitting. The Streamlit app
uses only the files generated here, where `id_student` is replaced by `anon_id`.
"""

from __future__ import annotations

import pandas as pd

try:
    from .config import BASE_KEY, CUTOFFS, FEATURE_PATHS, PROCESSED_DIR, RAW_DIR, ROOT
except ImportError:
    from config import BASE_KEY, CUTOFFS, FEATURE_PATHS, PROCESSED_DIR, RAW_DIR, ROOT

APP_DIR = ROOT / "data" / "app"
TEST_STUDENTS_PATH = PROCESSED_DIR / "test_students.csv"
APP_TEST_STUDENTS_PATH = APP_DIR / "app_test_students.csv"
APP_FEATURE_PATHS = {
    cutoff: APP_DIR / f"app_features_{cutoff}.csv"
    for cutoff in CUTOFFS
}


def load_feature_frames() -> dict[str, pd.DataFrame]:
    """Load all processed feature files."""
    frames = {}
    for cutoff, path in FEATURE_PATHS.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing feature file: {path.relative_to(ROOT)}")
        frames[cutoff] = pd.read_csv(path)
    return frames


def build_anonymization_map(frames: dict[str, pd.DataFrame], test_students: pd.DataFrame) -> pd.DataFrame:
    """Build a stable anon_id for every key used by app-facing files."""
    key_frames = [frame[BASE_KEY] for frame in frames.values()]
    key_frames.append(test_students[BASE_KEY])
    keys = pd.concat(key_frames, ignore_index=True).drop_duplicates(subset=BASE_KEY)
    keys = keys.sort_values(BASE_KEY).reset_index(drop=True)
    keys["anon_id"] = [f"STU{index + 1:06d}" for index in range(len(keys))]
    return keys


def load_final_result_labels() -> pd.DataFrame:
    """Load final_result for app display only."""
    label_path = RAW_DIR / "studentInfo.csv"
    if not label_path.exists():
        raise FileNotFoundError(f"Missing raw label file: {label_path.relative_to(ROOT)}")
    return pd.read_csv(label_path, usecols=BASE_KEY + ["final_result"], na_values="?")


def anonymize_features(frames: dict[str, pd.DataFrame], anon_map: pd.DataFrame) -> None:
    """Write app-facing feature files without id_student."""
    for cutoff, frame in frames.items():
        app_frame = frame.merge(anon_map, on=BASE_KEY, how="left", validate="many_to_one")
        if app_frame["anon_id"].isna().any():
            raise ValueError(f"{cutoff} has rows without anon_id")
        app_frame = app_frame.drop(columns=["id_student"])
        ordered_columns = ["anon_id", "code_module", "code_presentation"] + [
            column
            for column in app_frame.columns
            if column not in {"anon_id", "code_module", "code_presentation"}
        ]
        app_frame = app_frame[ordered_columns]
        output_path = APP_FEATURE_PATHS[cutoff]
        app_frame.to_csv(output_path, index=False)
        print(f"Wrote {output_path.relative_to(ROOT)} rows={len(app_frame)}")


def anonymize_test_students(test_students: pd.DataFrame, anon_map: pd.DataFrame) -> None:
    """Write app-facing test selector rows without id_student."""
    labels = load_final_result_labels()
    app_test = (
        test_students.merge(anon_map, on=BASE_KEY, how="left", validate="many_to_one")
        .merge(labels, on=BASE_KEY, how="left", validate="one_to_one")
    )
    if app_test["anon_id"].isna().any():
        raise ValueError("test_students has rows without anon_id")
    app_test = app_test.drop(columns=["id_student"])
    ordered_columns = ["anon_id", "code_module", "code_presentation", "final_result"] + [
        column
        for column in app_test.columns
        if column not in {"anon_id", "code_module", "code_presentation", "final_result"}
    ]
    app_test = app_test[ordered_columns]
    app_test.to_csv(APP_TEST_STUDENTS_PATH, index=False)
    print(f"Wrote {APP_TEST_STUDENTS_PATH.relative_to(ROOT)} rows={len(app_test)}")


def validate_app_files() -> None:
    """Ensure app-facing CSV files do not expose id_student."""
    paths = [APP_TEST_STUDENTS_PATH, *APP_FEATURE_PATHS.values()]
    for path in paths:
        frame = pd.read_csv(path, nrows=5)
        if "id_student" in frame.columns:
            raise ValueError(f"{path.relative_to(ROOT)} exposes id_student")
    print("Validated app-facing files: anon_id only, no id_student column.")


def main() -> None:
    """Create anonymized app-facing CSV files."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if not TEST_STUDENTS_PATH.exists():
        raise FileNotFoundError(f"Missing test student file: {TEST_STUDENTS_PATH.relative_to(ROOT)}")
    frames = load_feature_frames()
    test_students = pd.read_csv(TEST_STUDENTS_PATH)
    anon_map = build_anonymization_map(frames, test_students)
    anonymize_features(frames, anon_map)
    anonymize_test_students(test_students, anon_map)
    validate_app_files()


if __name__ == "__main__":
    main()
