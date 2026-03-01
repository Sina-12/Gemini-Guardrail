import csv
import random
import re
from collections import defaultdict, deque
from convokit import Corpus, download

# -----------------------------
# Configuration
# -----------------------------
CORPUS_PATH = r"C:\Users\leyao\.convokit\saved-corpora\winning-args-corpus" # Replace with your username, obviously
OUTPUT_FILE = r"data\winning_args_threads.csv"
MIN_LENGTH = 5          # minimum number of comments in a path
RANDOM_SEED = 67        # reproducibility

random.seed(RANDOM_SEED)

# -----------------------------
# Helper: Clean text
# -----------------------------
def clean_text(text):
    # Convert to string
    text = str(text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Truncate at marker if present
    marker = "*Hello, users of CMV!"
    idx = text.find(marker)
    if idx != -1:
        text = text[:idx]

    return text

# -----------------------------
# Load corpus
# -----------------------------
corpus = Corpus(CORPUS_PATH)
output_rows = []
pair_counter = 0

# -----------------------------
# Process conversations
# -----------------------------
for convo in corpus.iter_conversations():

    # Conversation-level OP info
    conv_meta = convo.meta
    op_speaker = conv_meta.get("op-userID", "OP")
    op_title = conv_meta.get("op-title", "")
    op_text_body = conv_meta.get("op-text-body", "")
    op_text = clean_text(f"{op_title} {op_text_body}")

    # Group utterances by pair_id
    pair_map = defaultdict(lambda: {"success": [], "unsuccess": []})
    for utt in convo.iter_utterances():
        pair_ids = utt.meta.get("pair_ids")
        success_label = utt.meta.get("success")
        if pair_ids is None or success_label is None:
            continue
        for pid in pair_ids:
            if success_label == 1:
                pair_map[pid]["success"].append(utt)
            elif success_label == 0:
                pair_map[pid]["unsuccess"].append(utt)

    for pid, data in pair_map.items():

        success_utts = data["success"]
        unsuccess_utts = data["unsuccess"]
        if not success_utts or not unsuccess_utts:
            continue

        # Helper: Build linear path from leaf to root
        def build_path(utts):
            utt_dict = {u.id: u for u in utts}
            leaf = None
            for u in utts:
                if not any(child.reply_to == u.id for child in utts):
                    leaf = u
                    break
            if leaf is None:
                return []
            path = []
            current = leaf
            while current:
                path.append(current)
                if current.reply_to in utt_dict:
                    current = utt_dict[current.reply_to]
                else:
                    break
            path = list(reversed(path))
            return path

        success_path = build_path(success_utts)
        unsuccess_path = build_path(unsuccess_utts)
        if len(success_path) + 1 < MIN_LENGTH or len(unsuccess_path) + 1 < MIN_LENGTH:
            continue  # +1 accounts for conv-level OP

        # -----------------------------
        # SUCCESS THREAD
        # -----------------------------
        success_id = f"{pair_counter}_s"
        replier_map = {}
        replier_count = 1

        # Add conversation-level OP as depth 0
        output_rows.append({
            "id": success_id,
            "success": 1,
            "speaker_id": f"{pair_counter}_s_OP",
            "text": op_text,
            "depth": 0
        })

        for depth, utt in enumerate(success_path, start=1):
            speaker = utt.speaker.id
            if speaker == op_speaker:
                speaker_label = f"{pair_counter}_s_OP"
            else:
                if speaker not in replier_map:
                    replier_map[speaker] = f"{pair_counter}_s_r{replier_count}"
                    replier_count += 1
                speaker_label = replier_map[speaker]

            output_rows.append({
                "id": success_id,
                "success": 1,
                "speaker_id": speaker_label,
                "text": clean_text(utt.text),
                "depth": depth
            })

        # -----------------------------
        # UNSUCCESSFUL THREAD
        # -----------------------------
        unsuccess_id = f"{pair_counter}_u"
        replier_map = {}
        replier_count = 1

        # Add conversation-level OP as depth 0
        output_rows.append({
            "id": unsuccess_id,
            "success": 0,
            "speaker_id": f"{pair_counter}_u_OP",
            "text": op_text,
            "depth": 0
        })

        for depth, utt in enumerate(unsuccess_path, start=1):
            speaker = utt.speaker.id
            if speaker == op_speaker:
                speaker_label = f"{pair_counter}_u_OP"
            else:
                if speaker not in replier_map:
                    replier_map[speaker] = f"{pair_counter}_u_r{replier_count}"
                    replier_count += 1
                speaker_label = replier_map[speaker]

            output_rows.append({
                "id": unsuccess_id,
                "success": 0,
                "speaker_id": speaker_label,
                "text": clean_text(utt.text),
                "depth": depth
            })

        pair_counter += 1

# -----------------------------
# Write CSV
# -----------------------------
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=["id", "success", "speaker_id", "text", "depth"]
    )
    writer.writeheader()
    writer.writerows(output_rows)

print(f"Export complete: {OUTPUT_FILE}")
