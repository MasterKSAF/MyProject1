from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

import fitz
import imageio_ffmpeg
from moviepy import AudioFileClip, ImageClip, concatenate_videoclips


PROJECT_ROOT = Path(__file__).resolve().parents[3]
STAGE_DIR = PROJECT_ROOT / "stages" / "stage7"
STAGE6_DIR = PROJECT_ROOT / "stages" / "stage6"
DEFAULT_PDF = STAGE6_DIR / "presentation" / "Presentation_google_slides_safe.pdf"
DEFAULT_SCRIPT = STAGE_DIR / "docs" / "stage7_demo_script.json"
DEFAULT_OUTPUT_DIR = STAGE_DIR / "docs" / "stage7_demo_build"
DEFAULT_OUTPUT_VIDEO = STAGE_DIR / "docs" / "stage7_defense_demo_ru.mp4"

VIDEO_SIZE = (1920, 1080)
FPS = 24
TAIL_PADDING = 0.35


def load_script(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dirs(base_dir: Path) -> tuple[Path, Path]:
    slides_dir = base_dir / "slides"
    audio_dir = base_dir / "audio"
    slides_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    return slides_dir, audio_dir


def render_slides(pdf_path: Path, slides_dir: Path, slide_count: int) -> list[Path]:
    doc = fitz.open(pdf_path)
    if doc.page_count < slide_count:
        raise ValueError(f"PDF has only {doc.page_count} slides, but script expects {slide_count}")

    paths: list[Path] = []
    for slide_idx in range(slide_count):
        out_path = slides_dir / f"slide_{slide_idx + 1:02d}.png"
        if not out_path.exists():
            page = doc.load_page(slide_idx)
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            pix.save(out_path)
        paths.append(out_path)
    doc.close()
    return paths


def synthesize_slide_audio(text: str, voice: str, rate: str, media_path: Path, text_path: Path) -> None:
    text_path.write_text(text, encoding="utf-8")
    command = [
        "edge-tts",
        "--file",
        str(text_path),
        "--voice",
        voice,
        f"--rate={rate}",
        "--write-media",
        str(media_path),
    ]
    subprocess.run(command, check=True)


def build_audio_assets(script_data: dict, audio_dir: Path) -> list[Path]:
    voice = script_data["voice"]
    rate = script_data["rate"]
    audio_paths: list[Path] = []

    for item in script_data["slides"]:
        slide_no = int(item["slide"])
        audio_path = audio_dir / f"slide_{slide_no:02d}.mp3"
        text_path = audio_dir / f"slide_{slide_no:02d}.txt"
        synthesize_slide_audio(item["text"], voice, rate, audio_path, text_path)
        audio_paths.append(audio_path)
    return audio_paths


def build_video(slide_paths: list[Path], audio_paths: list[Path], output_path: Path) -> None:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe

    clips = []
    audio_clips = []
    try:
        for slide_path, audio_path in zip(slide_paths, audio_paths, strict=True):
            audio_clip = AudioFileClip(str(audio_path))
            audio_clips.append(audio_clip)
            duration = audio_clip.duration + TAIL_PADDING
            video_clip = (
                ImageClip(str(slide_path))
                .resized(new_size=VIDEO_SIZE)
                .with_duration(duration)
                .with_audio(audio_clip)
            )
            clips.append(video_clip)

        final = concatenate_videoclips(clips, method="compose")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            ffmpeg_params=["-pix_fmt", "yuv420p"],
            logger="bar",
        )
        final.close()
    finally:
        for clip in clips:
            clip.close()
        for clip in audio_clips:
            clip.close()


def write_timing_file(script_data: dict, audio_paths: list[Path], output_path: Path) -> None:
    lines = [
        f"voice={script_data['voice']}",
        f"rate={script_data['rate']}",
        "",
    ]
    current = 0.0
    for item, audio_path in zip(script_data["slides"], audio_paths, strict=True):
        audio = AudioFileClip(str(audio_path))
        try:
            lines.append(
                f"{int(item['slide']):02d}. {item['title']} | start={current:.2f}s | tts={audio.duration:.2f}s"
            )
            current += audio.duration + TAIL_PADDING
        finally:
            audio.close()
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build narrated defense demo from slides and notes.")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-video", type=Path, default=DEFAULT_OUTPUT_VIDEO)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script_data = load_script(args.script)
    slides_dir, audio_dir = ensure_dirs(args.output_dir)
    slide_paths = render_slides(args.pdf, slides_dir, len(script_data["slides"]))
    audio_paths = build_audio_assets(script_data, audio_dir)
    write_timing_file(script_data, audio_paths, args.output_dir / "stage7_demo.timing.txt")
    build_video(slide_paths, audio_paths, args.output_video)
    print(args.output_video)


if __name__ == "__main__":
    main()
