import re
import shutil
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

BASE_DIR = Path(__file__).resolve().parent
BOOKS_DIR = BASE_DIR / "books"
QUOTES_FILE = BASE_DIR / "quotes.txt"
BACKUP_FILE = BASE_DIR / "quotes.backup.txt"
MAX_QUOTE_LENGTH = 1024
MIN_QUOTE_LENGTH = 60
AUTHOR = "Carlos Castaneda"

BOOK_TITLES = (
    ("The Teachings of Don Juan", "The Teachings of Don Juan"),
    ("Separate Reality", "A Separate Reality"),
    ("The Jorney to Ixtlan", "Journey to Ixtlan"),
    ("Tales of Power", "Tales of Power"),
    ("The Second Ring of Power", "The Second Ring of Power"),
    ("Eagle's Gift", "The Eagle's Gift"),
    ("The Fire From Within", "The Fire from Within"),
    ("The Power of Silence", "The Power of Silence"),
    ("The Art of dreaming", "The Art of Dreaming"),
    ("The Active Side of Infinity", "The Active Side of Infinity"),
)

SKIP_EXACT = {
    "Carlos Castaneda",
    "Index:",
    "Introduction",
    "Foreword",
    "Preface",
    "Authors Note",
    "File Info.",
}

SKIP_CONTAINS = {
    "controlledfolly@gmail.com",
    "tami-book.by.ru",
    "googlepages.com",
    "Original Illustration",
    "Home Location:",
    "PDF Version",
    "Taken from",
}

KEYWORDS = {
    "awareness",
    "controlled folly",
    "death",
    "dream",
    "dreaming",
    "energy",
    "freedom",
    "impeccable",
    "impeccability",
    "intent",
    "knowledge",
    "nagual",
    "perception",
    "personal history",
    "power",
    "recapitulation",
    "seeing",
    "seer",
    "self-importance",
    "silence",
    "sorcerer",
    "sorcery",
    "spirit",
    "stalking",
    "tonal",
    "warrior",
    "will",
    "world",
}

PRINCIPLE_PATTERNS = (
    r"\ba warrior\b",
    r"\bwarriors\b",
    r"\ba man of knowledge\b",
    r"\bman of knowledge\b",
    r"\ba sorcerer\b",
    r"\bsorcerers\b",
    r"\ba seer\b",
    r"\bseers\b",
    r"\bthe path\b",
    r"\bthe warrior'?s way\b",
    r"\bthe way of the warrior\b",
    r"\bdeath is\b",
    r"\bself-importance\b",
    r"\bpersonal history\b",
    r"\bcontrolled folly\b",
    r"\bimpeccability\b",
    r"\bimpeccable\b",
    r"\bintent\b",
    r"\bthe spirit\b",
    r"\bthe assemblage point\b",
    r"\bthe second attention\b",
    r"\bthe tonal\b",
    r"\bthe nagual\b",
    r"\brecapitulation\b",
    r"\bstalking\b",
    r"\bdreaming\b",
    r"\bsilence\b",
    r"\bfreedom\b",
)

CORE_TEACHING_PATTERNS = (
    r"\bthe (first|second|third|fourth) (principle|gate|attention|truth|rule)\b",
    r"\bprinciples? of stalking\b",
    r"\bthe art of stalking\b",
    r"\bthe art of dreaming\b",
    r"\bdreaming attention\b",
    r"\bassemblage point\b",
    r"\binternal dialogue\b",
    r"\binner silence\b",
    r"\bpersonal history\b",
    r"\bself-importance\b",
    r"\bcontrolled folly\b",
    r"\brecapitulation\b",
    r"\bimpeccability\b",
    r"\bimpeccable warrior\b",
    r"\bwarrior'?s way\b",
    r"\bpath of knowledge\b",
    r"\bman of knowledge\b",
    r"\bknowledge as power\b",
    r"\bthe spirit\b",
    r"\bintent\b",
    r"\bthe abstract\b",
    r"\bthe tonal\b",
    r"\bthe nagual\b",
    r"\bthe eagle\b",
    r"\bseeing\b",
    r"\bseer(s)?\b",
    r"\benergy body\b",
    r"\bsecond attention\b",
    r"\bthird attention\b",
)

INSTRUCTION_PATTERNS = (
    r"\byou must\b",
    r"\bone must\b",
    r"\ba warrior must\b",
    r"\bsorcerers must\b",
    r"\bdreamers must\b",
    r"\bhas to\b",
    r"\bhave to\b",
    r"\bneed to\b",
    r"\bin order to\b",
    r"\bthe first thing you have to do\b",
    r"\bthe only way\b",
    r"\bthe important thing\b",
    r"\bthe purpose\b",
    r"\bthe task\b",
    r"\bthe rule\b",
    r"\bthe reason\b",
    r"\bconsists of\b",
    r"\bmeans that\b",
    r"\bmeans to\b",
    r"\bis to\b",
    r"\bare to\b",
)

DRAMA_REJECT_PATTERNS = (
    r"\bcarcass\b",
    r"\bbottomless pit\b",
    r"\bgoats? always disappear\b",
    r"\bsupposed to die\b",
    r"\bone of us was supposed\b",
    r"\bawesome side\b",
    r"\bnot too far from here\b",
    r"\bwhere goats\b",
    r"\bcrack in the mountains\b",
    r"\bthrow your\b",
    r"\bkill(ed)?\b",
    r"\bmurder\b",
    r"\bcorpse\b",
    r"\bbody was\b",
    r"\bbody is\b",
    r"\bhe was afraid\b",
    r"\bshe was afraid\b",
    r"\bi was afraid\b",
    r"\bfrightened\b",
    r"\bterrified\b",
    r"\bhorrid time\b",
)

WEAK_STARTS = {
    "and ",
    "but ",
    "because ",
    "for ",
    "if ",
    "or ",
    "that ",
    "then ",
    "therefore ",
    "thus ",
    "when ",
    "while ",
}

QUESTION_STARTS = {
    "are ",
    "can ",
    "could ",
    "did ",
    "do ",
    "does ",
    "how ",
    "is ",
    "should ",
    "what ",
    "when ",
    "where ",
    "who ",
    "why ",
    "would ",
}

WEAK_ENDS = {
    "a",
    "an",
    "and",
    "as",
    "because",
    "but",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "or",
    "that",
    "the",
    "to",
    "with",
}

DIALOGUE_MARKERS = (
    "i asked",
    "i said",
    "he said",
    "she said",
    "don juan said",
    "don juan replied",
    "don juan answered",
    "he replied",
    "he answered",
)

TEACHING_PATTERNS = (
    r"\bis\b",
    r"\bare\b",
    r"\bmeans?\b",
    r"\bcalled\b",
    r"\bmust\b",
    r"\bhave to\b",
    r"\bneed to\b",
    r"\bshould\b",
    r"\bcan\b",
    r"\bcannot\b",
    r"\bcan't\b",
    r"\bnever\b",
    r"\balways\b",
    r"\bonly\b",
    r"\bbecause\b",
    r"\bin order to\b",
    r"\bthe reason\b",
    r"\bthe way\b",
    r"\bthe rule\b",
    r"\bthe point\b",
    r"\bthe problem\b",
    r"\bthe secret\b",
    r"\bthe task\b",
    r"\bthe art\b",
    r"\bthe mastery\b",
    r"\blearn\b",
    r"\bteach\b",
    r"\bunderstand\b",
    r"\bexplain\b",
)

CASUAL_PATTERNS = (
    r"\bi had gone\b",
    r"\bi woke up\b",
    r"\bi was in\b",
    r"\bi felt\b",
    r"\bi could feel\b",
    r"\bi found myself\b",
    r"\bi began to\b",
    r"\bi started to\b",
    r"\bi sat\b",
    r"\bi stood\b",
    r"\bi walked\b",
    r"\bi went\b",
    r"\bi ran\b",
    r"\bi drove\b",
    r"\bi returned\b",
    r"\bi arrived\b",
    r"\bi left\b",
    r"\bi stayed\b",
    r"\bi slept\b",
    r"\bi looked\b",
    r"\bi saw\b",
    r"\bi focused\b",
    r"\bi moved\b",
    r"\bi used\b",
    r"\bi played\b",
    r"\bi vomited\b",
    r"\bi gagged\b",
    r"\bi noticed\b",
    r"\bi remembered\b",
    r"\bi thought\b",
    r"\bi realized\b",
    r"\bi wanted\b",
    r"\bi decided\b",
    r"\bi asked\b",
    r"\bmy well-being\b",
    r"\bmy mood\b",
    r"\bmy body\b",
    r"\bmy fear\b",
    r"\bmy anxiety\b",
    r"\bi should have been\b",
    r"\bi was facing\b",
    r"\bi was alone\b",
    r"\bi was a warrior-traveler\b",
    r"\bat ship's\b",
    r"\bin l\.a\.\b",
    r"\bin los angeles\b",
)

SCENE_PATTERNS = (
    r"\ball of a sudden\b",
    r"\bat that moment\b",
    r"\bdarkness had descended\b",
    r"\bthe foliage\b",
    r"\bthe trees\b",
    r"\bthe dogs?\b",
    r"\bthe house\b",
    r"\bthe car\b",
    r"\bthe restaurant\b",
    r"\bthe kitchen\b",
    r"\bdona soledad\b",
    r"\bdon genaro\b",
    r"\bgenaro\b",
    r"\beligio\b",
    r"\bthe little sisters\b",
    r"\bthe genaros\b",
    r"\bla gorda\b",
    r"\bbenigno\b",
    r"\bnestor\b",
    r"\bpablito\b",
    r"\blidia\b",
    r"\bflorinda laughed\b",
    r"\bgrabbed\b",
    r"\bstood up\b",
    r"\bgot up\b",
    r"\bsat down\b",
    r"\bwalked\b",
    r"\bran\b",
    r"\bdrove\b",
    r"\barrived\b",
    r"\btears\b",
    r"\bhowls\b",
    r"\bbump on the head\b",
    r"\bmedicinal plants\b",
    r"\bbreakfast\b",
    r"\bmoney\b",
    r"\bfather\b",
)

REJECT_STORY_PATTERNS = (
    r"\bfew pesos\b",
    r"\bmy boss\b",
    r"\bgrandpa\b",
    r"\bhard worker\b",
    r"\bthe shop\b",
    r"\bcarried anything\b",
    r"\bcracked them every time\b",
    r"\bdamn chair\b",
    r"\bjackass\b",
    r"\bfather is as crazy\b",
    r"\bfather and a husband\b",
    r"\bmy father\b",
    r"\bmy grandfather\b",
    r"\bbreakfast\b",
    r"\bpurse strings\b",
    r"\bgroceries\b",
    r"\bthe waitress\b",
    r"\bthe restaurant\b",
    r"\bship's\b",
    r"\bthe parking lot\b",
    r"\bthe bus depot\b",
    r"\bthe bus station\b",
    r"\bthe church\b",
    r"\bpeople gossiped\b",
    r"\bwitnessed the incident\b",
    r"\bthe girl\b",
    r"\bthe horses\b",
    r"\bmy leg\b",
    r"\bthe stench\b",
    r"\bi took my most trusted servants\b",
    r"\bi was pretty miserable\b",
    r"\bi was hungry\b",
    r"\bi was tired\b",
    r"\bi was exhausted\b",
    r"\bi was sleepy\b",
    r"\bi ate\b",
    r"\bi vomited\b",
    r"\bi gagged\b",
    r"\bi parked\b",
    r"\bi got out\b",
    r"\bhe gave me something out\b",
    r"\bwhere did they go\b",
    r"\byou mean you don't know\b",
    r"\bsaid good-bye to me\b",
    r"\bsight of myself lying sound asleep\b",
    r"\bwake up, screaming\b",
    r"\bscreaming at the top of my voice\b",
    r"\bphysical discomfort\b",
    r"\bbordered on anguish\b",
    r"\bcomplained about the vivid dreams\b",
    r"\bhe seemed to deliberate\b",
    r"\bblow you kisses\b",
    r"\bacross the street\b",
    r"\bcontinued asking him questions\b",
    r"\bcarol tiggs\b",
    r"\bthe scout\b",
    r"\bin my case\b",
    r"\bthere was never\b",
    r"\bthe west has\b",
    r"\bthe south has\b",
    r"\bluminous bodies\b",
    r"\bmountain lion\b",
    r"\bjaguar\b",
    r"\bwhat had remained with me\b",
    r"\bi thought i knew\b",
    r"\bintroduce me to\b",
    r"\bone of his warriors whom i had not met\b",
    r"\bgo to her house\b",
    r"\bgo to his house\b",
    r"\bwhatever transpired between\b",
    r"\bwas of no concern to others\b",
    r"\bflorinda and myself\b",
    r"\bla gorda and myself\b",
    r"\bhis companions\b",
    r"\bher house\b",
    r"\bhis house\b",
    r"\bsaying good-bye to her house\b",
    r"\bi had been joyful\b",
    r"\bi related to them\b",
    r"\bstrike it rich\b",
    r"\bshe said and laughed\b",
    r"\bpretended to be old\b",
    r"\btheir captor\b",
    r"\bwhen he woke up\b",
    r"\blook at that man over there\b",
    r"\btreated him like dirt\b",
    r"\btoo coarse\b",
    r"\btoo stupid\b",
    r"\bwe rushed all night\b",
    r"\bafraid that you were dead\b",
    r"\bthe only one we should help\b",
    r"\bnearly died in there\b",
    r"\bwhispered in my right ear\b",
    r"\banother statement\b",
    r"\bi immediately began to protest\b",
    r"\bdon juan interrupted me\b",
    r"\bdon juan and i sat in silence\b",
    r"\bdon juan reiterated\b",
    r"\bi reiterated my profound disagreement\b",
    r"\bstifling religious environment\b",
    r"\bobedience dogma\b",
    r"\berratic mind\b",
    r"\bnot even curious\b",
    r"\bwe stopped at the bottom\b",
    r"\bthey headed for\b",
    r"\bthe place where we stood\b",
    r"\bi automatically\b",
    r"\bi said to them\b",
    r"\bi wanted to\b",
    r"\bi had witnessed\b",
    r"\bi asked half in jest\b",
    r"\bhe vaguely heard\b",
    r"\bshe thought that\b",
    r"\bthey all laughed\b",
    r"\beverybody laughed\b",
    r"\bwe were sitting\b",
    r"\bwe walked\b",
    r"\bwe arrived\b",
    r"\bwhen we arrived\b",
    r"\bas she got out\b",
    r"\btears swelled\b",
)

WEAK_TRAILING_PATTERNS = (
    r"\bhe went on\.?$",
    r"\bdon juan went on\.?$",
    r"\bshe went on\.?$",
    r"\bhe continued\.?$",
    r"\bshe continued\.?$",
    r"\bhe said to me\.?$",
    r"\bshe said to me\.?$",
    r"\bi asked\.?$",
    r"\bi said\.?$",
)


def natural_sort_key(value):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value.name)
    ]


def extract_pdf_sections(path):
    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    starts = []

    for index, text in enumerate(pages):
        header = text[:500]

        if "book in the series" not in header:
            continue

        for raw_title, canonical_title in BOOK_TITLES:
            if raw_title in header:
                starts.append((index, canonical_title))
                break

    if not starts:
        return [(path.stem, "\n".join(pages))]

    sections = []

    for position, (start_index, title) in enumerate(starts):
        end_index = starts[position + 1][0] if position + 1 < len(starts) else len(pages)
        sections.append((title, "\n".join(pages[start_index:end_index])))

    return sections


def should_skip_line(line):
    stripped = line.strip()

    if not stripped:
        return True
    if stripped in SKIP_EXACT:
        return True
    if stripped.isdigit():
        return True
    if any(part in stripped for part in SKIP_CONTAINS):
        return True
    if re.fullmatch(r"[-\s]+", stripped):
        return True
    if re.search(r"\.{5,}\s*\d+$", stripped):
        return True
    if re.fullmatch(r"(Chapter|Part)\s+\d+.*", stripped, re.IGNORECASE):
        return True
    if re.fullmatch(r"\d+\.\s+[A-Z].*", stripped):
        return True
    if stripped.endswith("book in the series."):
        return True
    if stripped.startswith("-Cover") or stripped.startswith("-Contact"):
        return True

    return False


def clean_text(raw_text):
    lines = []

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()

        if should_skip_line(line):
            continue

        lines.append(line)

    text = " ".join(lines)
    text = re.sub(r"-\s+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"\b1\b", "I", text)

    return text.strip()


def split_sentences(text):
    return re.split(r"(?<=[.!?])\s+(?=[\"A-Z])", text)


def normalize_quote(text):
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("- ,")
    text = text.strip()

    if text and text[-1] not in ".!?":
        text += "."

    return text


def looks_useful(text):
    lower = text.lower()
    words = re.findall(r"[A-Za-z']+", lower)

    if len(text) < MIN_QUOTE_LENGTH or len(text) > MAX_QUOTE_LENGTH:
        return False
    if text.rstrip('"').endswith("?"):
        return False
    if any(lower.startswith(start) for start in WEAK_STARTS):
        return False
    if lower.endswith(("i asked.", "he asked.", "she asked.", "i said.", "he said.", "she said.")):
        return False
    if words and words[-1] in WEAK_ENDS:
        return False
    if "@" in text or "http" in lower or "www." in lower:
        return False
    if text[0] in ".,;:)]}":
        return False
    if text[0].islower():
        return False
    if "?" in text:
        return False
    if text.count('"') > 2:
        return False
    if any(lower.startswith(start) for start in WEAK_STARTS):
        return False
    if any(lower.startswith(start) for start in QUESTION_STARTS):
        return False
    if re.search(r"\b(i asked|he asked|she asked|i said|he said|she said)\b", lower):
        return False
    if lower.count("chapter") > 1 or lower.count("index") > 1:
        return False
    if not any(keyword in lower for keyword in KEYWORDS):
        return False
    if not has_teaching_value(text, is_dialogue=False):
        return False
    if is_mostly_personal_recap(text) and '"' not in text:
        return False
    if teaching_score(text) < 3:
        return False
    if len(re.findall(r"[A-Za-z]", text)) < 50:
        return False

    return True


def looks_like_dialogue(text):
    lower = text.lower()
    words = re.findall(r"[A-Za-z']+", lower)

    if len(text) < MIN_QUOTE_LENGTH or len(text) > MAX_QUOTE_LENGTH:
        return False
    if text.rstrip('"').endswith("?"):
        return False
    if any(lower.startswith(start) for start in WEAK_STARTS):
        return False
    if lower.endswith(("i asked.", "he asked.", "she asked.", "i said.", "he said.", "she said.")):
        return False
    if words and words[-1] in WEAK_ENDS:
        return False
    if "?" not in text:
        return False
    if text[0] in ".,;:)]}" or text[0].islower():
        return False
    if "@" in text or "http" in lower or "www." in lower:
        return False
    if text.count('"') < 2:
        return False
    if not any(marker in lower for marker in DIALOGUE_MARKERS):
        return False
    if not any(keyword in lower for keyword in KEYWORDS):
        return False
    if not has_teaching_value(text, is_dialogue=True):
        return False
    if teaching_score(text) < 1:
        return False
    if len(re.findall(r"[A-Za-z]", text)) < 50:
        return False

    return True


def teaching_score(text):
    lower = text.lower()
    score = 0

    score += sum(1 for pattern in TEACHING_PATTERNS if re.search(pattern, lower))
    score += sum(1 for keyword in KEYWORDS if keyword in lower)
    score += sum(2 for pattern in PRINCIPLE_PATTERNS if re.search(pattern, lower))
    score -= sum(1 for pattern in CASUAL_PATTERNS if re.search(pattern, lower))
    score -= sum(1 for pattern in SCENE_PATTERNS if re.search(pattern, lower))

    if '"' in text:
        score += 1
    if "?" in text:
        score += 1
    if re.search(r"\b(man|men|warrior|sorcerer|seer|person|people|human beings)\b", lower):
        score += 1

    return score


def has_teaching_value(text, is_dialogue):
    lower = text.lower()
    principle_hits = sum(1 for pattern in PRINCIPLE_PATTERNS if re.search(pattern, lower))
    teaching_hits = sum(1 for pattern in TEACHING_PATTERNS if re.search(pattern, lower))
    casual_hits = sum(1 for pattern in CASUAL_PATTERNS if re.search(pattern, lower))
    scene_hits = sum(1 for pattern in SCENE_PATTERNS if re.search(pattern, lower))
    reject_story_hits = sum(1 for pattern in REJECT_STORY_PATTERNS if re.search(pattern, lower))
    score = teaching_score(text)

    if reject_story_hits:
        return False

    if any(re.search(pattern, lower) for pattern in WEAK_TRAILING_PATTERNS):
        return False

    if re.search(r"\bi (then )?(used|focused|looked|saw|moved|walked|ran|played|vomited)\b", lower):
        if principle_hits == 0 and not is_dialogue:
            return False

    if scene_hits >= 2 and principle_hits < 2:
        return False

    if casual_hits + scene_hits >= 3 and principle_hits == 0:
        return False

    if lower.startswith(("i ", "my ")) and principle_hits == 0 and '"' not in text:
        return False

    if is_dialogue:
        return score >= 4 and (principle_hits > 0 or teaching_hits >= 3)

    return score >= 5 and (principle_hits > 0 or teaching_hits >= 4)


def has_didactic_value(text):
    lower = text.lower()

    if any(re.search(pattern, lower) for pattern in REJECT_STORY_PATTERNS):
        return False
    if any(re.search(pattern, lower) for pattern in DRAMA_REJECT_PATTERNS):
        return False
    if any(re.search(pattern, lower) for pattern in WEAK_TRAILING_PATTERNS):
        return False

    core_hits = sum(1 for pattern in CORE_TEACHING_PATTERNS if re.search(pattern, lower))
    instruction_hits = sum(1 for pattern in INSTRUCTION_PATTERNS if re.search(pattern, lower))
    principle_hits = sum(1 for pattern in PRINCIPLE_PATTERNS if re.search(pattern, lower))
    teaching_hits = sum(1 for pattern in TEACHING_PATTERNS if re.search(pattern, lower))
    casual_hits = sum(1 for pattern in CASUAL_PATTERNS if re.search(pattern, lower))
    scene_hits = sum(1 for pattern in SCENE_PATTERNS if re.search(pattern, lower))

    if core_hits == 0:
        return False

    if instruction_hits == 0 and principle_hits == 0 and teaching_hits < 3:
        return False

    if casual_hits + scene_hits > 3:
        return False

    if text.startswith(("I ", "My ")) and instruction_hits == 0:
        return False

    return True


def is_mostly_personal_recap(text):
    lower = text.lower()
    personal_hits = sum(1 for pattern in CASUAL_PATTERNS if re.search(pattern, lower))
    teaching_hits = sum(1 for pattern in TEACHING_PATTERNS if re.search(pattern, lower))

    if personal_hits >= 2 and teaching_hits <= 2:
        return True

    if lower.startswith(("i ", "my ")) and personal_hits >= 1 and teaching_hits <= 3:
        return True

    return False


def sentence_has_dialogue(sentence):
    lower = sentence.lower()
    return '"' in sentence or "?" in sentence or any(
        marker in lower for marker in DIALOGUE_MARKERS
    )


def build_dialogue_candidates(sentences):
    candidates = []
    index = 0

    while index < len(sentences):
        sentence = sentences[index]

        if "?" not in sentence:
            index += 1
            continue

        block = []
        cursor = index
        saw_answer_after_question = False

        while cursor < len(sentences) and len(" ".join(block)) < MAX_QUOTE_LENGTH:
            current = sentences[cursor]

            if cursor > index and saw_answer_after_question and "?" in current:
                break

            candidate = normalize_quote(" ".join(block + [current]))

            if len(candidate) > MAX_QUOTE_LENGTH:
                break

            block.append(current)

            if cursor > index and (
                '"' in current
                or any(marker in current.lower() for marker in DIALOGUE_MARKERS)
            ):
                saw_answer_after_question = True

            if saw_answer_after_question and cursor > index:
                next_sentence = sentences[cursor + 1] if cursor + 1 < len(sentences) else ""
                if "?" in next_sentence:
                    break
                if not sentence_has_dialogue(next_sentence):
                    break
                if len(normalize_quote(" ".join(block + [next_sentence]))) > MAX_QUOTE_LENGTH:
                    break

            cursor += 1

        quote = normalize_quote(" ".join(block))

        if saw_answer_after_question and looks_like_dialogue(quote):
            candidates.append(quote)
            index = max(cursor, index + 1)
        else:
            index += 1

    return candidates


def build_candidates(text):
    sentences = [normalize_quote(sentence) for sentence in split_sentences(text)]
    sentences = [sentence for sentence in sentences if sentence]
    candidates = build_dialogue_candidates(sentences)

    index = 0
    while index < len(sentences):
        best_quote = None
        best_size = 0

        for size in (3, 2, 1):
            if index + size > len(sentences):
                continue

            quote = normalize_quote(" ".join(sentences[index:index + size]))

            if looks_useful(quote):
                best_quote = quote
                best_size = size
                break

        if best_quote:
            candidates.append(best_quote)
            index += best_size
        else:
            index += 1

    return candidates


def add_source(quote, book_title):
    quote = normalize_quote(quote)
    source = f"\n\n— {AUTHOR}, {book_title}"
    max_body_length = MAX_QUOTE_LENGTH - len(source)

    if len(quote) > max_body_length:
        return None

    return quote + source


def dedupe_quotes(quotes):
    unique = []
    seen = set()

    for quote in quotes:
        key = re.sub(r"[^a-z0-9]+", " ", quote.lower()).strip()
        compact_key = key[:180]

        if key in seen or compact_key in seen:
            continue

        seen.add(key)
        seen.add(compact_key)
        unique.append(quote)

    return unique


def main():
    pdf_files = sorted(BOOKS_DIR.glob("*.pdf"), key=natural_sort_key)

    if not pdf_files:
        raise RuntimeError("No PDF files found in books/")

    all_candidates = []

    for pdf_file in pdf_files:
        print(f"Reading {pdf_file.name}")
        sections = extract_pdf_sections(pdf_file)

        for book_title, raw_text in sections:
            clean = clean_text(raw_text)
            candidates = [
                sourced_quote
                for quote in build_candidates(clean)
                if (sourced_quote := add_source(quote, book_title))
            ]
            all_candidates.extend(candidates)
            print(f"{book_title}: {len(candidates)}")

    quotes = dedupe_quotes(all_candidates)

    backup_file = None

    if QUOTES_FILE.exists():
        if BACKUP_FILE.exists():
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_file = BASE_DIR / f"quotes.backup.{timestamp}.txt"
        else:
            backup_file = BACKUP_FILE

        shutil.copy2(QUOTES_FILE, backup_file)

    QUOTES_FILE.write_text("\n\n---\n\n".join(quotes) + "\n", encoding="utf-8")

    print(f"Saved quotes: {len(quotes)}")
    print(f"Output: {QUOTES_FILE}")
    if backup_file:
        print(f"Backup: {backup_file}")


if __name__ == "__main__":
    main()
