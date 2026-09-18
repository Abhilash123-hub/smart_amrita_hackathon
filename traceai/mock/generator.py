"""Mock corpus and dirty dataset generator for TraceAI testing and evaluation."""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


# 10 Classical excerpt templates for simulated copyrighted works
BASE_EXCERPTS = [
    ("Moby Dick by Herman Melville", "Call me Ishmael. Some years ago - never mind how long precisely - having little or no money in my purse, and nothing particular to interest me on shore, I thought I would sail about a little and see the watery part of the world."),
    ("Pride and Prejudice by Jane Austen", "It is a truth universally acknowledged, that a single man in possession of a good fortune, must be in want of a wife. However little known the feelings or views of such a man may be."),
    ("Tale of Two Cities by Charles Dickens", "It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of foolishness, it was the epoch of belief, it was the epoch of incredulity."),
    ("Frankenstein by Mary Shelley", "You will rejoice to hear that no disaster has accompanied the commencement of an enterprise which you have regarded with such evil forebodings. I arrived here yesterday."),
    ("The Great Gatsby by F. Scott Fitzgerald", "In my younger and more vulnerable years my father gave me some advice that I've been turning over in my mind ever since. Whenever you feel like criticizing anyone, just remember."),
    ("The Odyssey by Homer", "Sing to me of the man, Muse, the man of twists and turns driven time and again off course, once he had plundered the hallowed heights of Troy."),
    ("1984 by George Orwell", "It was a bright cold day in April, and the clocks were striking thirteen. Winston Smith, his chin nuzzled into his breast in an effort to escape the vile wind, slipped quickly."),
    ("The Metamorphosis by Franz Kafka", "One morning, when Gregor Samsa woke from troubled dreams, he found himself transformed in his bed into a horrible vermin. He lay on his armour-like back."),
    ("The Raven by Edgar Allan Poe", "Once upon a midnight dreary, while I pondered, weak and weary, Over many a quaint and curious volume of forgotten lore—While I nodded, nearly napping, suddenly there came a tapping."),
    ("Alice in Wonderland by Lewis Carroll", "Alice was beginning to get very tired of sitting by her sister on the bank, and of having nothing to do: once or twice she had peeped into the book her sister was reading.")
]

# Paraphrased variants designed to test cross-encoder re-ranker sensitivity
PARAPHRASED_EXCERPTS = [
    ("Ishmael is my name. Years ago, without much money left in my pockets and nothing holding me ashore, I decided to take a voyage across the oceans of the world.", "Moby Dick by Herman Melville"),
    ("Everybody knows that an unmarried wealthy gentleman is undoubtedly seeking a spouse, regardless of what his actual personal desires might be.", "Pride and Prejudice by Jane Austen"),
    ("Those were our greatest days and yet our most dreadful moments, an era filled with profound brilliance and supreme folly, faith alongside sheer skepticism.", "Tale of Two Cities by Charles Dickens"),
    ("You'll be delighted that everything began safely on this expedition you worried over so dreadfully. My arrival here was recorded just yesterday.", "Frankenstein by Mary Shelley"),
    ("When I was younger, my dad offered me guidance that has stayed in my thoughts ever since: when tempted to judge someone, keep in mind their background.", "The Great Gatsby by F. Scott Fitzgerald")
]


def create_gradient_image(color1: tuple, color2: tuple, width: int = 256, height: int = 256, label: str = "") -> Image.Image:
    """Generate a distinct test image with a gradient and label."""
    img = Image.new("RGB", (width, height), color1)
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(color1[0] + (color2[0] - color1[0]) * (y / height))
        g = int(color1[1] + (color2[1] - color1[1]) * (y / height))
        b = int(color1[2] + (color2[2] - color1[2]) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    # Draw simple shapes
    draw.ellipse([width // 4, height // 4, 3 * width // 4, 3 * height // 4], outline=(255, 255, 255), width=4)
    if label:
        draw.text((10, 10), label, fill=(255, 255, 255))
    return img


def generate_mock_corpus(base_dir: Path | str) -> dict:
    """Generate copyright index (50 texts, 50 images) and dirty dataset (10 files)."""
    root = Path(base_dir).resolve()
    index_dir = root / "copyright_index"
    dirty_dir = root / "dirty_dataset"
    index_text_dir = index_dir / "texts"
    index_img_dir = index_dir / "images"

    for d in [index_text_dir, index_img_dir, dirty_dir]:
        d.mkdir(parents=True, exist_ok=True)

    index_metadata = {"texts": [], "images": []}

    # 1. Generate 50 Copyright Text Excerpts
    for i in range(50):
        title, text = BASE_EXCERPTS[i % len(BASE_EXCERPTS)]
        full_text = f"[{title} - Part {i // len(BASE_EXCERPTS) + 1}]\n{text}\nCopyright (c) Protected Literary Archive. All Rights Reserved."
        file_path = index_text_dir / f"copyright_work_{i+1:03d}.txt"
        file_path.write_text(full_text, encoding="utf-8")
        index_metadata["texts"].append({
            "id": f"work_txt_{i+1:03d}",
            "file": file_path.name,
            "source": f"© {title}",
            "sample": text[:80]
        })

    # NYT Copyrighted Tech Archive Excerpt (Demonstration Corpus Match)
    nyt_path = index_text_dir / "copyright_work_nyt_994.txt"
    nyt_path.write_text(
        "The proprietary transformer architecture incorporates a multi-tier attention mechanism "
        "specifically designed to retain contextual embeddings across ultra-long document contexts "
        "exceeding 128k tokens. RefCorpus: New York Times 2023 Tech Archive (Doc #994). All rights reserved.",
        encoding="utf-8"
    )
    index_metadata["texts"].append({
        "id": "work_txt_nyt_994",
        "file": nyt_path.name,
        "source": "RefCorpus: New York Times 2023 Tech Archive (Doc #994)",
        "sample": "The proprietary transformer architecture incorporates a multi-tier attention"
    })

    # Linux Kernel GPL Code Excerpt (Demonstration Codebase Match)
    index_code_dir = index_dir / "code"
    index_code_dir.mkdir(parents=True, exist_ok=True)
    code_path = index_code_dir / "kernel_sched.c"
    code_path.write_text(
        "/* SPDX-License-Identifier: GPL-2.0 */\n"
        "/* GNU General Public License v2.0 */\n"
        "/* RefCorpus: GitHub Linux GPL-2.0 Kernel Subsystem */\n"
        "static inline int trace_event_raw_event_sched_switch(struct trace_event_file *file, void *data) {\n"
        "    return 0;\n"
        "}\n",
        encoding="utf-8"
    )

    # 2. Generate 50 Copyright Images
    colors = [
        ((230, 50, 50), (30, 50, 200)),
        ((30, 180, 80), (240, 220, 20)),
        ((120, 40, 180), (240, 120, 30)),
        ((20, 150, 220), (20, 20, 20)),
        ((250, 100, 150), (50, 100, 250)),
    ]
    for i in range(50):
        c1, c2 = colors[i % len(colors)]
        img = create_gradient_image(c1, c2, 256, 256, label=f"Copyright Art #{i+1}")
        file_path = index_img_dir / f"copyright_img_{i+1:03d}.png"
        img.save(file_path, format="PNG")
        index_metadata["images"].append({
            "id": f"work_img_{i+1:03d}",
            "file": file_path.name,
            "source": f"© Visual Arts Archive #{i+1}",
        })

    (index_dir / "metadata.json").write_text(json.dumps(index_metadata, indent=2), encoding="utf-8")

    # 3. Generate Dirty Ingestion Dataset (10 files)
    # 5 paraphrased text files labeled .public_domain
    for j in range(5):
        paraphrase_text, original_source = PARAPHRASED_EXCERPTS[j]
        dirty_file = dirty_dir / f"book_excerpt_{j+1:02d}.public_domain"
        # Content contains paraphrased text intentionally designed to evade naive lexical search
        dirty_file.write_text(
            f"Public Domain Research Scrape:\n{paraphrase_text}\nScraped from open web.",
            encoding="utf-8"
        )

    # 5 cropped/resized image files labeled .public_domain
    for j in range(5):
        c1, c2 = colors[j % len(colors)]
        base_img = create_gradient_image(c1, c2, 256, 256, label=f"Copyright Art #{j+1}")
        # Crop 15% edges and resize slightly to test CLIP visual invariance
        cropped = base_img.crop((20, 20, 236, 236)).resize((250, 250))
        dirty_img = dirty_dir / f"art_scan_{j+1:02d}.public_domain"
        # Saved as PNG bytes despite misleading .public_domain extension
        cropped.save(dirty_img, format="PNG")

    return {
        "index_dir": str(index_dir),
        "dirty_dir": str(dirty_dir),
        "total_index_works": 100,
        "dirty_files_count": 10
    }
