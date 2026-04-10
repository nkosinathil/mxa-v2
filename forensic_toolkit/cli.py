import argparse
import os
import sys

from .runner import run_analysis


def build_parser():
    parser = argparse.ArgumentParser(
        prog="forensic_toolkit",
        description="MxA Communication Intelligence Toolkit"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to the input evidence folder"
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path to the output folder"
    )

    parser.add_argument(
        "--case-no",
        default="CASE-001",
        help="Case number for case-based output"
    )

    parser.add_argument(
        "--transcribe-audio",
        action="store_true",
        help="Enable .opus transcription. Disabled by default because it can take a long time."
    )

    parser.add_argument(
        "--audio-max-seconds",
        type=float,
        default=None,
        help="Optional maximum duration in seconds for audio transcription. Longer files are indexed but not transcribed."
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    output_path = os.path.abspath(args.output)
    case_no = args.case_no
    transcribe_audio = bool(args.transcribe_audio)
    audio_max_seconds = args.audio_max_seconds

    if not os.path.exists(input_path):
        print(f"[error] Input path does not exist: {input_path}")
        sys.exit(1)

    if not os.path.isdir(input_path):
        print(f"[error] Input path must be a folder: {input_path}")
        sys.exit(1)

    os.makedirs(output_path, exist_ok=True)

    def progress(msg):
        print(msg)

    try:
        summary = run_analysis(
            input_path=input_path,
            output_path=output_path,
            case_no=case_no,
            progress=progress,
            transcribe_audio=transcribe_audio,
            audio_max_transcription_seconds=audio_max_seconds
        )
    except KeyboardInterrupt:
        print("[error] Analysis interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"[error] Analysis failed: {exc}")
        sys.exit(1)

    print("")
    print("[done] Analysis complete")
    print(f"[done] Case folder: {summary.get('case_dir', '')}")
    print(f"[done] SQLite DB: {summary.get('db_path', '')}")
    print(f"[done] Communications: {summary.get('records', 0)}")
    print(f"[done] Attachments: {summary.get('attachments', 0)}")
    print(f"[done] Missing artifacts: {summary.get('missing', 0)}")
    print(f"[done] Media files: {summary.get('media_files', 0)}")
    print("")
    print("[done] Open the dashboard here:")
    print(os.path.join(summary.get("case_dir", ""), "dashboard", "index.html"))


if __name__ == "__main__":
    main()