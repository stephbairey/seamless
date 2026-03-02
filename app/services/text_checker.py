"""Text checker service — AI tells detection, em dash enforcement, structural analysis.

Three tiers:
  Tier 1 (regex, fast, deterministic): banned vocabulary, basic pattern detection, em dashes
  Tier 2 (structural): paragraph/sentence uniformity, anaphora
  Tier 3 (heuristic, higher false-positive): -ing clauses, promotional enthusiasm, etc.
"""

import re
import statistics
from typing import Any

from app.models.identity import Violation
from app.services.yaml_store import yaml_store


class TextChecker:
    def __init__(self):
        self._ai_tells = None
        self._em_dash_rules = None

    def _load(self):
        self._ai_tells = yaml_store.read("ai-tells.yaml")
        self._em_dash_rules = yaml_store.read("em-dash-rules.yaml")

    def _ensure_loaded(self):
        if self._ai_tells is None:
            self._load()

    def reload(self):
        self._ai_tells = None
        self._em_dash_rules = None
        self._load()

    def check(self, text: str, voice_id: str = "") -> list[Violation]:
        """Run all tiers of checks."""
        self._ensure_loaded()
        violations = []
        violations.extend(self._check_banned_vocabulary(text))
        violations.extend(self._check_banned_patterns_regex(text))
        violations.extend(self._check_em_dashes(text, voice_id))
        violations.extend(self._check_structural(text))
        violations.extend(self._check_heuristic(text))
        return violations

    def check_tier1(self, text: str, voice_id: str = "") -> list[Violation]:
        """Tier 1 only — fast checks for real-time use."""
        self._ensure_loaded()
        violations = []
        violations.extend(self._check_banned_vocabulary(text))
        violations.extend(self._check_banned_patterns_regex(text))
        violations.extend(self._check_em_dashes(text, voice_id))
        return violations

    # --- Tier 1: Regex-based ---

    def _check_banned_vocabulary(self, text: str) -> list[Violation]:
        violations = []
        for entry in self._ai_tells.get("banned_vocabulary", []):
            pattern = entry.get("pattern", "")
            if not pattern:
                continue
            for match in re.finditer(pattern, text, re.IGNORECASE):
                violations.append(Violation(
                    rule_id=f"vocab-{entry['word'].replace(' ', '-')}",
                    label=f"Banned word: {entry['word']}",
                    severity=entry.get("severity", "high"),
                    description=f"'{entry['word']}' is on the AI tells blacklist.",
                    matched_text=match.group(),
                    position=match.start(),
                    line=text[:match.start()].count("\n") + 1,
                    suggestion=entry.get("suggestion"),
                ))
        return violations

    def _check_banned_patterns_regex(self, text: str) -> list[Violation]:
        violations = []
        for entry in self._ai_tells.get("banned_patterns", []):
            if entry.get("detection_type") != "regex":
                continue
            pattern = entry.get("pattern", "")
            if not pattern:
                continue
            flags = re.MULTILINE | re.IGNORECASE
            for match in re.finditer(pattern, text, flags):
                violations.append(Violation(
                    rule_id=entry["pattern_id"],
                    label=entry["label"],
                    severity=entry.get("severity", "medium"),
                    description=entry.get("description", ""),
                    matched_text=match.group(),
                    position=match.start(),
                    line=text[:match.start()].count("\n") + 1,
                    suggestion=entry.get("suggestion"),
                ))
        return violations

    def _check_em_dashes(self, text: str, voice_id: str) -> list[Violation]:
        if not voice_id:
            return []

        mode = self._get_em_dash_mode(voice_id)
        if mode == "na":
            # Still flag if em dashes present — they'd be out of character
            mode = "banned"

        violations = []
        detection = self._em_dash_rules.get("detection", {})
        any_pattern = detection.get("patterns", {}).get("any_em_dash", "[\u2014\u2015]|--")

        for match in re.finditer(any_pattern, text):
            pos = match.start()
            line_num = text[:pos].count("\n") + 1
            context_snippet = text[max(0, pos - 30):min(len(text), pos + 30)]

            if mode == "banned":
                violations.append(Violation(
                    rule_id="em-dash-banned",
                    label="Em dash (banned in this context)",
                    severity="high",
                    description=f"Em dashes are banned in {voice_id} context. Zero allowed.",
                    matched_text=match.group(),
                    position=pos,
                    line=line_num,
                    suggestion="Remove the em dash. Use a period, comma, colon, or restructure.",
                ))
            elif mode == "restricted":
                # Check if it's a valid parenthetical (paired em dashes mid-sentence)
                if not self._is_valid_parenthetical(text, pos):
                    violations.append(Violation(
                        rule_id="em-dash-restricted",
                        label="Em dash (restricted use)",
                        severity="medium",
                        description="Em dashes are only permitted as mid-sentence parentheticals (paired). This one appears to extend a thought.",
                        matched_text=context_snippet.strip(),
                        position=pos,
                        line=line_num,
                        suggestion="Use paired em dashes as parentheticals, or remove.",
                    ))

        return violations

    def _get_em_dash_mode(self, voice_id: str) -> str:
        """Determine em dash mode for a given voice_id."""
        modes = self._em_dash_rules.get("modes", {})
        for mode_name, mode_data in modes.items():
            for ctx in mode_data.get("contexts", []):
                if ctx.get("voice_id") == voice_id:
                    return mode_name
        return "restricted"  # default

    def _is_valid_parenthetical(self, text: str, pos: int) -> bool:
        """Check if an em dash at pos is part of a valid parenthetical pair."""
        em_dash_pattern = re.compile("[\u2014\u2015]|--")
        # Find all em dash positions in the same sentence
        # Get sentence boundaries
        sentence_start = max(text.rfind(".", 0, pos), text.rfind("!", 0, pos), text.rfind("?", 0, pos)) + 1
        sentence_end_match = re.search(r"[.!?]", text[pos:])
        sentence_end = pos + sentence_end_match.start() if sentence_end_match else len(text)

        sentence = text[sentence_start:sentence_end]
        dashes_in_sentence = list(em_dash_pattern.finditer(sentence))

        # Valid parenthetical = exactly 2 em dashes in the sentence, not at start/end
        if len(dashes_in_sentence) == 2:
            first_pos = dashes_in_sentence[0].start()
            last_pos = dashes_in_sentence[1].start()
            sentence_stripped = sentence.strip()
            # Neither at the very beginning nor very end of sentence
            if first_pos > 2 and last_pos < len(sentence_stripped) - 2:
                return True

        return False

    # --- Tier 2: Structural ---

    def _check_structural(self, text: str) -> list[Violation]:
        violations = []
        violations.extend(self._check_uniform_paragraph_length(text))
        violations.extend(self._check_uniform_sentence_rhythm(text))
        violations.extend(self._check_anaphora(text))
        return violations

    def _check_uniform_paragraph_length(self, text: str) -> list[Violation]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if len(paragraphs) < 3:
            return []

        word_counts = [len(p.split()) for p in paragraphs]
        mean_wc = statistics.mean(word_counts)
        if mean_wc == 0:
            return []

        spread = (max(word_counts) - min(word_counts)) / mean_wc
        if spread < 0.20:
            return [Violation(
                rule_id="uniform-paragraph-length",
                label="Uniform paragraph length",
                severity="medium",
                description=f"All {len(paragraphs)} paragraphs are within {spread:.0%} word count of each other (threshold: 20%). This is an AI tell.",
                matched_text=None,
                suggestion="Vary paragraph lengths for more natural rhythm.",
                confidence="medium",
            )]
        return []

    def _check_uniform_sentence_rhythm(self, text: str) -> list[Violation]:
        sentences = re.split(r"[.!?]+\s+", text.strip())
        sentences = [s for s in sentences if s.strip()]
        if len(sentences) < 5:
            return []

        lengths = [len(s.split()) for s in sentences]
        std_dev = statistics.stdev(lengths)
        if std_dev < 3:
            return [Violation(
                rule_id="uniform-sentence-rhythm",
                label="Uniform sentence rhythm",
                severity="medium",
                description=f"Sentence length standard deviation is {std_dev:.1f} words (threshold: <3). Sentences are too similar in length.",
                matched_text=None,
                suggestion="Mix short and long sentences for more natural rhythm.",
                confidence="medium",
            )]
        return []

    def _check_anaphora(self, text: str) -> list[Violation]:
        sentences = re.split(r"[.!?]+\s+", text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) < 3:
            return []

        violations = []
        run_start = 0
        for i in range(1, len(sentences)):
            prev_first = sentences[i - 1].split()[0].lower() if sentences[i - 1].split() else ""
            curr_first = sentences[i].split()[0].lower() if sentences[i].split() else ""

            if curr_first != prev_first:
                run_length = i - run_start
                if run_length >= 3:
                    word = sentences[run_start].split()[0]
                    violations.append(Violation(
                        rule_id="anaphora",
                        label="Anaphora",
                        severity="medium",
                        description=f"{run_length} consecutive sentences start with '{word}'.",
                        matched_text=f"{sentences[run_start][:50]}...",
                        suggestion="Vary sentence openings.",
                    ))
                run_start = i

        # Check final run
        run_length = len(sentences) - run_start
        if run_length >= 3:
            word = sentences[run_start].split()[0]
            violations.append(Violation(
                rule_id="anaphora",
                label="Anaphora",
                severity="medium",
                description=f"{run_length} consecutive sentences start with '{word}'.",
                matched_text=f"{sentences[run_start][:50]}...",
                suggestion="Vary sentence openings.",
            ))

        return violations

    # --- Tier 3: Heuristic ---

    def _check_heuristic(self, text: str) -> list[Violation]:
        violations = []
        violations.extend(self._check_tailing_ing(text))
        violations.extend(self._check_promotional_enthusiasm(text))
        violations.extend(self._check_emotional_hollowness(text))
        violations.extend(self._check_weasel_wording(text))
        violations.extend(self._check_problem_solution(text))
        return violations

    def _check_tailing_ing(self, text: str) -> list[Violation]:
        violations = []
        pattern = r",\s+\w+ing\s+[^.]*\.$"
        for match in re.finditer(pattern, text, re.MULTILINE):
            violations.append(Violation(
                rule_id="tailing-ing",
                label="Tailing -ing clause",
                severity="low",
                description="Sentence ends with a participial (-ing) phrase.",
                matched_text=match.group().strip(),
                position=match.start(),
                line=text[:match.start()].count("\n") + 1,
                suggestion="Consider restructuring to avoid the trailing participial phrase.",
                confidence="low",
            ))
        return violations

    def _check_promotional_enthusiasm(self, text: str) -> list[Violation]:
        violations = []

        # Exclamation mark density
        word_count = len(text.split())
        if word_count > 0:
            excl_count = text.count("!")
            per_500 = (excl_count / word_count) * 500
            threshold = 2
            if per_500 > threshold:
                violations.append(Violation(
                    rule_id="promotional-enthusiasm-exclamation",
                    label="Promotional enthusiasm (exclamation marks)",
                    severity="medium",
                    description=f"{excl_count} exclamation marks in {word_count} words ({per_500:.1f} per 500 words, threshold: {threshold}).",
                    matched_text=None,
                    suggestion="Tone down promotional language. Let the work speak for itself.",
                    confidence="medium",
                ))

        # Superlative clustering
        superlatives = ["amazing", "incredible", "extraordinary", "revolutionary",
                        "transformative", "game-changing", "unparalleled", "unprecedented"]
        found = []
        for word in superlatives:
            for match in re.finditer(rf"\b{word}\b", text, re.IGNORECASE):
                found.append(match.group())
        if len(found) >= 2:
            violations.append(Violation(
                rule_id="promotional-enthusiasm-superlatives",
                label="Promotional enthusiasm (superlative clustering)",
                severity="medium",
                description=f"Found {len(found)} superlatives: {', '.join(found)}.",
                matched_text=", ".join(found),
                suggestion="Tone down promotional language. Use specifics instead of superlatives.",
                confidence="medium",
            ))

        return violations

    def _check_emotional_hollowness(self, text: str) -> list[Violation]:
        violations = []
        phrases = [
            "passionate about", "deeply committed to", "truly believes in",
            "making a difference", "changing lives", "world-class",
            "best-in-class", "thought leader", "at the end of the day",
            "moving the needle",
        ]
        for phrase in phrases:
            for match in re.finditer(re.escape(phrase), text, re.IGNORECASE):
                violations.append(Violation(
                    rule_id="emotional-hollowness",
                    label="Emotional hollowness",
                    severity="medium",
                    description=f"Generic praise phrase: '{phrase}'.",
                    matched_text=match.group(),
                    position=match.start(),
                    line=text[:match.start()].count("\n") + 1,
                    suggestion="Replace with specific, concrete details.",
                    confidence="medium",
                ))
        return violations

    def _check_weasel_wording(self, text: str) -> list[Violation]:
        violations = []
        pattern = r"\b(?:[Mm]any (?:people|experts|studies)|[Ii]t is (?:widely |generally )?(?:believed|known|accepted|thought)|[Ss]ome (?:say|argue|believe)|[Rr]esearch (?:shows|suggests|indicates))\b"
        for match in re.finditer(pattern, text):
            violations.append(Violation(
                rule_id="weasel-wording",
                label="Weasel wording",
                severity="low",
                description="Vague attribution.",
                matched_text=match.group(),
                position=match.start(),
                line=text[:match.start()].count("\n") + 1,
                suggestion="Attribute specifically or state directly.",
                confidence="low",
            ))
        return violations

    def _check_problem_solution(self, text: str) -> list[Violation]:
        problem_words = {"struggle", "challenge", "problem", "pain point", "frustrated"}
        solution_words = {"solution", "answer", "here's how", "that's where", "the good news"}

        sentences = re.split(r"[.!?]+\s+", text)
        violations = []

        for i, sentence in enumerate(sentences):
            s_lower = sentence.lower()
            has_problem = any(w in s_lower for w in problem_words)
            if has_problem:
                # Check next 3 sentences for solution words
                for j in range(i + 1, min(i + 4, len(sentences))):
                    s2_lower = sentences[j].lower()
                    if any(w in s2_lower for w in solution_words):
                        violations.append(Violation(
                            rule_id="problem-solution-formula",
                            label="Problem-solution formula",
                            severity="low",
                            description="Formulaic problem-then-solution pattern detected.",
                            matched_text=f"{sentence[:40]}... → ...{sentences[j][:40]}",
                            suggestion="Restructure to avoid the formulaic problem-then-solution pattern.",
                            confidence="low",
                        ))
                        break

        return violations
