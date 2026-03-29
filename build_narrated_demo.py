from __future__ import annotations

import math
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageFilter


ROOT = Path("/Users/ae23069/Desktop/encode_fellowship_demo")
PREVIEWS = ROOT / "assets" / "previews"
OUTDIR = ROOT / "output_narrated"
SLIDES = OUTDIR / "slides"

W = 1920
H = 1080

BG = "#f4efe6"
INK = "#142033"
MUTED = "#58657c"
ACCENT = "#0f8c8c"
ACCENT_2 = "#d67b2c"
PANEL = "#fbf8f2"
LINE = "#d8d0c4"

FONT_TITLE = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
FONT_BODY = "/System/Library/Fonts/Supplemental/Avenir Next.ttc"
FONT_MONO = "/System/Library/Fonts/Supplemental/Menlo.ttc"

SEGMENTS = [
    {
        "slide": "01_cover.png",
        "text": "This demo is a quick walkthrough of valley-k-small, the research system I use to study first-passage-time distributions in stochastic search, and why I think this kind of work can become useful scientific tooling.",
    },
    {
        "slide": "02_problem.png",
        "text": "The scientific question is simple to state, but rich in behaviour. If a random walker moves on a ring with a directed shortcut, how does that geometry reshape the full distribution of arrival times, not just the mean? I care about the whole curve: the first peak, the valley between peaks, the possibility of a second peak, and the parameter regimes that create those transitions.",
    },
    {
        "slide": "03_repo.png",
        "text": "What I am proud of here is not only the mathematics. It is the structure of the project. This is not a single notebook with a few nice plots. The repository already separates reports, reusable core code in src slash vkcore, archives, documentation, and site outputs. Individual report folders then keep their own code, figures, data, notes, sections, and outputs. That makes the work reproducible and easier to extend.",
    },
    {
        "slide": "04_workflow.png",
        "text": "The workflow is equally important. I can define a geometry, sweep a parameter such as beta or shortcut destination, regenerate outputs, and compare exact and numerical behaviour inside the same loop. That means I am not relying on visual intuition alone. I can turn a question into a clean computational experiment and then into figures and report-ready conclusions.",
    },
    {
        "slide": "05_beta.png",
        "text": "One example is the beta sweep. By changing only beta, I can see how peak timings move, how the bimodal window changes, and how the entire first-passage curve deforms.",
    },
    {
        "slide": "06_destination.png",
        "text": "Another example is the destination scan, where I vary only the shortcut destination and compare exact curves, peak locations, and second-peak behaviour across cases.",
    },
    {
        "slide": "07_distribution.png",
        "text": "The broader point is that I keep the whole distribution in view. Instead of collapsing everything to one summary statistic, I can reason about early and late subpopulations, valley depth, and shortcut-driven transitions in a much more rigorous way.",
    },
    {
        "slide": "08_bridge.png",
        "text": "Why does that matter beyond theory? Because the same pipeline can become a decision tool. In BioPath, I want to use movement models and spatial structure to support precision pest management, especially questions like trap placement and spatial search design. So this fellowship would not be a pivot away from my current work. It would be a way to turn a rigorous research pipeline into a model-based product for real scientific and operational decisions.",
    },
]


def font(path: str, size: int):
    return ImageFont.truetype(path, size=size)


def f_title(size: int):
    return font(FONT_TITLE, size)


def f_body(size: int):
    return font(FONT_BODY, size)


def f_mono(size: int):
    return font(FONT_MONO, size)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def ffprobe_duration(path: Path) -> float:
    out = subprocess.check_output(
        [
            "/opt/homebrew/bin/ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nk=1:nw=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(out)


def wrap(draw: ImageDraw.ImageDraw, text: str, width: int, font_obj) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if draw.textbbox((0, 0), candidate, font=font_obj)[2] <= width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def draw_paragraph(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], font_obj, fill=INK, line_gap: int = 10):
    x0, y0, x1, y1 = box
    lines = wrap(draw, text, x1 - x0, font_obj)
    y = y0
    for line in lines:
        draw.text((x0, y), line, font=font_obj, fill=fill)
        h = draw.textbbox((0, 0), line, font=font_obj)[3]
        y += h + line_gap
        if y > y1:
            break


def fit_title(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], max_size: int = 78, min_size: int = 42, fill=INK):
    x0, y0, x1, y1 = box
    for size in range(max_size, min_size - 1, -2):
        font_obj = f_title(size)
        lines = wrap(draw, text, x1 - x0, font_obj)
        heights = [draw.textbbox((0, 0), line, font=font_obj)[3] for line in lines]
        total = sum(heights) + 12 * max(len(lines) - 1, 0)
        if total <= (y1 - y0) and len(lines) <= 3:
            y = y0
            for line, h in zip(lines, heights):
                draw.text((x0, y), line, font=font_obj, fill=fill)
                y += h + 12
            return
    draw.text((x0, y0), text, font=f_title(min_size), fill=fill)


def load_chart(path: Path, size: tuple[int, int]) -> Image.Image:
    img = Image.open(path).convert("RGB")
    bg = Image.new("RGB", img.size, "#ffffff")
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    img = img.crop(bbox or (0, 0, img.width, img.height))
    img.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "#ffffff")
    ox = (size[0] - img.width) // 2
    oy = (size[1] - img.height) // 2
    canvas.paste(img, (ox, oy))
    return canvas


def base_slide(section: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((-200, -100, 700, 600), fill=(119, 180, 170, 40))
    gd.ellipse((1100, 300, 2100, 1300), fill=(235, 176, 112, 36))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, W, 22), fill=INK)
    draw.text((70, 70), section, font=f_body(30), fill=ACCENT)
    return img, draw


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str | None = None):
    draw.rounded_rectangle(box, radius=28, fill=PANEL, outline=LINE, width=2)
    if title:
        draw.text((box[0] + 28, box[1] + 22), title, font=f_body(28), fill=ACCENT)


def slide_cover():
    img, draw = base_slide("ENCODE FELLOWSHIP DEMO")
    fit_title(draw, "valley-k-small", (90, 150, 900, 280), max_size=84, min_size=56)
    draw_paragraph(
        draw,
        "A technical walkthrough of a reproducible research system for first-passage-time distributions on ring networks with directed shortcuts.",
        (95, 310, 870, 470),
        f_body(40),
        fill=ACCENT,
        line_gap=12,
    )
    draw_paragraph(
        draw,
        "The aim here is simple: show the science, the workflow, and the path from theory to a real decision tool.",
        (95, 520, 900, 720),
        f_body(28),
        fill=MUTED,
        line_gap=10,
    )
    card(draw, (980, 140, 1830, 930), "Representative curve")
    chart = load_chart(PREVIEWS / "N100_K4_beta002.f_t.pdf.png", (790, 720))
    img.paste(chart, (1010, 190))
    img.save(SLIDES / "01_cover.png")


def slide_problem():
    img, draw = base_slide("SCIENTIFIC QUESTION")
    fit_title(draw, "What changes when a shortcut reshapes the whole distribution?", (90, 140, 1250, 300), max_size=74, min_size=48)
    draw_paragraph(
        draw,
        "The project is not about a single mean arrival time. It tracks the full first-passage-time curve: peak timing, valley depth, second-peak emergence, and the regimes that create those transitions.",
        (95, 320, 980, 520),
        f_body(30),
        fill=MUTED,
        line_gap=10,
    )

    cx, cy, r = 410, 760, 190
    pts: list[tuple[int, int]] = []
    for i in range(12):
        ang = math.radians(i * 30)
        pts.append((int(cx + r * math.cos(ang)), int(cy + r * math.sin(ang))))
    for i, (px, py) in enumerate(pts):
        nx, ny = pts[(i + 1) % len(pts)]
        draw.line((px, py, nx, ny), fill="#4d6387", width=5)
    for i, (px, py) in enumerate(pts):
        color = "#d6dce6"
        if i == 0:
            color = ACCENT
        if i == 6:
            color = ACCENT_2
        draw.ellipse((px - 18, py - 18, px + 18, py + 18), fill=color, outline=INK, width=2)
    draw.line((pts[0][0], pts[0][1], pts[4][0], pts[4][1]), fill=ACCENT, width=6)
    draw.polygon(
        [(pts[4][0], pts[4][1]), (pts[4][0] - 18, pts[4][1] - 10), (pts[4][0] - 12, pts[4][1] + 16)],
        fill=ACCENT,
    )
    draw.text((245, 980), "ring network + directed shortcut", font=f_body(24), fill=MUTED)

    card(draw, (1040, 420, 1830, 930), "What the outputs reveal")
    bullets = [
        "The bimodality window moves when beta changes.",
        "Peak times shift differently for different K.",
        "The shortcut destination controls whether the second peak survives.",
        "Those effects can be compared exactly, not just visually.",
    ]
    y = 510
    for text in bullets:
        draw.ellipse((1080, y + 8, 1100, y + 28), fill=ACCENT)
        draw_paragraph(draw, text, (1125, y, 1775, y + 80), f_body(28), fill=INK)
        y += 95
    img.save(SLIDES / "02_problem.png")


def slide_repo():
    img, draw = base_slide("REPO EVIDENCE")
    fit_title(draw, "The repo already behaves like a research system", (90, 140, 1650, 260), max_size=72, min_size=48)
    draw_paragraph(
        draw,
        "The strongest signal is structural, not cosmetic: reports, reusable core code, archives, docs, and site outputs already live in explicit places instead of a single notebook.",
        (95, 285, 1750, 390),
        f_body(28),
        fill=MUTED,
        line_gap=8,
    )

    card(draw, (95, 450, 840, 930), "Root structure")
    root_text = ".\n├── reports/\n├── src/vkcore/\n├── docs/\n├── archives/\n├── site/\n├── scripts/\n└── schemas/"
    draw.multiline_text((135, 510), root_text, font=f_mono(34), fill=ACCENT, spacing=10)

    card(draw, (930, 450, 1680, 930), "One report folder")
    report_text = "reports/ring_lazy_jump_ext/\n├── code/\n├── figures/\n├── data/\n├── outputs/\n├── notes/\n├── sections/\n└── tables/"
    draw.multiline_text((970, 510), report_text, font=f_mono(32), fill=ACCENT, spacing=10)

    draw.line((840, 690, 930, 690), fill=ACCENT, width=8)
    draw.polygon([(930, 690), (900, 674), (900, 706)], fill=ACCENT)

    card(draw, (95, 960, 1680, 1035), None)
    draw_paragraph(
        draw,
        "That split makes the project reproducible: theory, experiments, figures, and writing can all be regenerated and checked independently.",
        (130, 975, 1645, 1028),
        f_body(26),
        fill=INK,
        line_gap=8,
    )
    img.save(SLIDES / "03_repo.png")


def slide_workflow():
    img, draw = base_slide("RESEARCH WORKFLOW")
    fit_title(draw, "The workflow connects theory, sweeps, and report outputs", (90, 140, 1700, 260), max_size=70, min_size=48)
    draw_paragraph(
        draw,
        "A question can be turned into a geometry, a parameter scan, and then a comparable set of exact and numerical outputs inside one loop.",
        (95, 285, 1730, 380),
        f_body(28),
        fill=MUTED,
        line_gap=8,
    )

    boxes = [
        ((95, 430, 560, 720), "Model", "define the ring, shortcut, and target geometry"),
        ((610, 430, 1075, 720), "Sweep", "scan beta or destination and regenerate structured outputs"),
        ((1125, 430, 1590, 720), "Report", "compare curves, peak metrics, and final figures"),
    ]
    for box, title, text in boxes:
        card(draw, box, title)
        draw_paragraph(draw, text, (box[0] + 28, box[1] + 95, box[2] - 28, box[3] - 30), f_body(34), fill=INK)
    draw.line((560, 575, 610, 575), fill=ACCENT, width=6)
    draw.line((1075, 575, 1125, 575), fill=ACCENT, width=6)

    card(draw, (95, 790, 1590, 985), "Why this matters")
    draw_paragraph(
        draw,
        "That is what makes the project extensible. I am not relying on visual intuition alone, and I do not need to rebuild the workflow every time the question changes.",
        (130, 845, 1545, 945),
        f_body(30),
        fill=INK,
        line_gap=10,
    )
    img.save(SLIDES / "04_workflow.png")


def slide_beta():
    img, draw = base_slide("BETA SWEEP")
    fit_title(draw, "Changing one parameter already moves the regime structure", (90, 140, 1700, 260), max_size=70, min_size=48)
    draw_paragraph(
        draw,
        "The beta scan makes two things visible at once: when peak timings shift, and where bimodality still survives.",
        (95, 285, 1700, 370),
        f_body(28),
        fill=MUTED,
        line_gap=8,
    )

    card(draw, (95, 420, 920, 960), "Peak-time shift")
    card(draw, (1000, 420, 1825, 960), "Bimodality flags")
    chart1 = load_chart(PREVIEWS / "scan_beta_N100_peak_times.pdf.png", (770, 450))
    chart2 = load_chart(PREVIEWS / "scan_beta_N100_bimodality.pdf.png", (770, 450))
    img.paste(chart1, (122, 500))
    img.paste(chart2, (1027, 500))
    img.save(SLIDES / "05_beta.png")


def slide_destination():
    img, draw = base_slide("DESTINATION SCAN")
    fit_title(draw, "Varying the shortcut destination reveals where the second peak survives", (90, 140, 1760, 260), max_size=66, min_size=44)
    draw_paragraph(
        draw,
        "This is where the work becomes especially concrete: I change only the destination and compare exact cases, peak positions, and second-peak height across the family.",
        (95, 285, 1710, 380),
        f_body(28),
        fill=MUTED,
        line_gap=8,
    )

    card(draw, (95, 420, 1000, 960), "Selected exact cases")
    card(draw, (1080, 420, 1825, 960), "Second-peak height vs destination")
    chart1 = load_chart(PREVIEWS / "exact_selected_cases.pdf.png", (850, 470))
    chart2 = load_chart(PREVIEWS / "peak2_vs_dst.pdf.png", (690, 470))
    img.paste(chart1, (122, 470))
    img.paste(chart2, (1108, 500))
    img.save(SLIDES / "06_destination.png")


def slide_distribution():
    img, draw = base_slide("WHY THE WHOLE CURVE MATTERS")
    fit_title(draw, "The full distribution reveals more than a single summary statistic", (90, 140, 1750, 260), max_size=68, min_size=44)
    draw_paragraph(
        draw,
        "Keeping the whole curve in view makes it possible to talk about early and late subpopulations, valley depth, and shortcut-driven transitions with much more precision.",
        (95, 285, 1710, 380),
        f_body(28),
        fill=MUTED,
        line_gap=8,
    )

    card(draw, (95, 420, 920, 960), "Representative curve")
    card(draw, (1000, 420, 1825, 960), "Shortcut usage vs peak structure")
    chart1 = load_chart(PREVIEWS / "N100_K4_beta002.f_t.pdf.png", (770, 470))
    chart2 = load_chart(PREVIEWS / "pcross_relationships.pdf.png", (770, 470))
    img.paste(chart1, (122, 500))
    img.paste(chart2, (1027, 500))
    img.save(SLIDES / "07_distribution.png")


def slide_bridge():
    img, draw = base_slide("BIOPATH BRIDGE")
    fit_title(draw, "From stochastic search theory to a real decision tool", (90, 140, 1650, 260), max_size=72, min_size=48)
    draw_paragraph(
        draw,
        "The fellowship case is not that this is already a product. It is that the same modelling pipeline can become decision support for spatial search and trap placement.",
        (95, 285, 1650, 390),
        f_body(28),
        fill=MUTED,
        line_gap=8,
    )
    card(draw, (95, 440, 820, 940), "Today")
    card(draw, (1100, 440, 1825, 940), "Next")
    left = [
        "first-passage-time distributions",
        "exact and numerical comparison",
        "peak / valley regime identification",
        "reproducible scientific outputs",
    ]
    right = [
        "movement models in real spaces",
        "trap-placement recommendations",
        "clearer parameter trade-offs",
        "decision support for BioPath",
    ]
    y = 535
    for text in left:
        draw.ellipse((135, y + 7, 155, y + 27), fill=ACCENT)
        draw_paragraph(draw, text, (180, y, 760, y + 70), f_body(30), fill=INK)
        y += 90
    y = 535
    for text in right:
        draw.ellipse((1140, y + 7, 1160, y + 27), fill=ACCENT_2)
        draw_paragraph(draw, text, (1185, y, 1765, y + 70), f_body(30), fill=INK)
        y += 90
    draw.line((845, 685, 1075, 685), fill=ACCENT, width=8)
    draw.polygon([(1075, 685), (1048, 671), (1048, 699)], fill=ACCENT)
    draw.text((900, 635), "translation", font=f_body(28), fill=ACCENT)
    img.save(SLIDES / "08_bridge.png")


def fmt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def build_subtitles(audio_path: Path) -> None:
    entries: list[str] = []
    clock = 0.0
    idx = 1
    durations = compute_segment_durations(audio_path)
    for seg, seg_duration in zip(SEGMENTS, durations):
        words = seg["text"].split()
        chunk_size = 10
        chunks = [" ".join(words[i : i + chunk_size]) for i in range(0, len(words), chunk_size)]
        total_words = max(len(words), 1)
        running = 0
        for chunk in chunks:
            count = len(chunk.split())
            start = clock + seg_duration * (running / total_words)
            running += count
            end = clock + seg_duration * (running / total_words)
            entries.append(f"{idx}\n{fmt_time(start)} --> {fmt_time(end)}\n{chunk}\n")
            idx += 1
        clock += seg_duration

    (OUTDIR / "captions.srt").write_text("\n".join(entries) + "\n", encoding="utf-8")


def compute_segment_durations(audio_path: Path) -> list[float]:
    total_duration = ffprobe_duration(audio_path)
    word_counts = [len(seg["text"].split()) for seg in SEGMENTS]
    total_words = sum(word_counts)
    durations = [total_duration * (count / total_words) for count in word_counts]
    return durations


def build_video(audio_path: Path) -> None:
    durations = compute_segment_durations(audio_path)
    cmd = ["/opt/homebrew/bin/ffmpeg", "-y"]
    filters = []
    concat_inputs = []
    for i, (seg, dur) in enumerate(zip(SEGMENTS, durations)):
        cmd.extend(["-loop", "1", "-t", f"{dur:.3f}", "-i", str(SLIDES / seg["slide"])])
        filters.append(
            f"[{i}:v]fps=25,scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p,setsar=1[v{i}]"
        )
        concat_inputs.append(f"[v{i}]")
    filters.append("".join(concat_inputs) + f"concat=n={len(SEGMENTS)}:v=1:a=0[v]")
    cmd.extend(
        [
            "-i",
            str(audio_path),
            "-i",
            str(OUTDIR / "captions.srt"),
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[v]",
            "-map",
            f"{len(SEGMENTS)}:a",
            "-map",
            f"{len(SEGMENTS)+1}:s",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-c:s",
            "mov_text",
            "-shortest",
            str(OUTDIR / "final_demo.mp4"),
        ]
    )
    run(cmd)


def write_notes(audio_path: Path) -> None:
    total = ffprobe_duration(audio_path)
    note = (
        f"Audio source: {audio_path}\n"
        f"Total duration: {total:.1f} seconds\n"
        "Stable URL target: https://raw.githubusercontent.com/zhouyi-xiaoxiao/encode-fellowship-demo/main/latest_demo.mp4\n"
    )
    (OUTDIR / "build_notes.txt").write_text(note, encoding="utf-8")


def build_slides() -> None:
    slide_cover()
    slide_problem()
    slide_repo()
    slide_workflow()
    slide_beta()
    slide_destination()
    slide_distribution()
    slide_bridge()


DEFAULT_AUDIO_PATH = "/Users/ae23069/Desktop/encode_fellowship_demo/voice_clone_pipeline/chatterbox_full_v1/full_take_master.wav"


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    SLIDES.mkdir(parents=True, exist_ok=True)
    build_slides()
    audio_path = Path(os.environ.get("DEMO_AUDIO_PATH", DEFAULT_AUDIO_PATH))
    build_subtitles(audio_path)
    build_video(audio_path)
    write_notes(audio_path)


if __name__ == "__main__":
    main()
