"""Shared video-quality settings for every MoneyPrint renderer.

Why this exists: each renderer used to hard-code ``-preset veryfast -crf 23-27``
and untagged colours. On the dark, flat, gradient-heavy slides that produces
visible banding, blocky shadows and a colour shift (swscale defaults to BT.601
while players assume BT.709 for HD). Keep the knobs in one place.

Override without code changes (useful on slow runners)::

    MONEYPRINT_X264_PRESET=veryfast MONEYPRINT_X264_CRF=21 python ...
"""
from __future__ import annotations

import os

DEFAULT_PRESET = "medium"
DEFAULT_CRF = 18

# Intermediate files (captures, converted GIFs, stock transcodes) are re-encoded
# later, so they should be near-transparent; generation loss compounds.
INTERMEDIATE_CRF = 16

_VALID_PRESETS = {"ultrafast", "superfast", "veryfast", "faster", "fast",
                  "medium", "slow", "slower", "veryslow"}


def preset() -> str:
    value = os.environ.get("MONEYPRINT_X264_PRESET", DEFAULT_PRESET).strip().lower()
    return value if value in _VALID_PRESETS else DEFAULT_PRESET


def crf(default: int = DEFAULT_CRF) -> int:
    try:
        value = int(os.environ.get("MONEYPRINT_X264_CRF", default))
    except (TypeError, ValueError):
        return default
    return value if 0 <= value <= 35 else default


def x264_args(*, crf_value: int | None = None, preset_value: str | None = None,
              threads: int | None = None) -> list[str]:
    """Final-delivery H.264 arguments (BT.709 tagged, dark-scene friendly).

    ``aq-mode=3`` shifts bits to dark, flat areas where banding is most visible;
    ``deblock`` slightly negative keeps fine text edges crisp.
    """
    args = [
        "-c:v", "libx264",
        "-preset", preset_value or preset(),
        "-crf", str(crf_value if crf_value is not None else crf()),
        "-x264-params", "aq-mode=3:deblock=-1,-1",
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709", "-color_primaries", "bt709",
        "-color_trc", "bt709", "-color_range", "tv",
    ]
    if threads:
        args += ["-threads", str(threads)]
    return args


def intermediate_args() -> list[str]:
    """Near-lossless, fast arguments for files that will be re-encoded."""
    return ["-c:v", "libx264", "-preset", "veryfast",
            "-crf", str(INTERMEDIATE_CRF), "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709",
            "-color_trc", "bt709"]


# swscale option string to append to scale filters that end in yuv420p.
SCALE_FLAGS = "flags=lanczos+accurate_rnd+full_chroma_int:out_color_matrix=bt709"
