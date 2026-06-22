from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    matched: bool
    confidence: float
    reason: str


class HoldDetector:
    strong_phrases = (
        "please hold",
        "hold for the next",
        "next available representative",
        "next available agent",
        "your call is important",
        "all representatives are currently assisting",
        "estimated wait time",
        "remain on the line",
        "stay on the line",
        "we will be with you shortly",
    )
    weak_phrases = (
        "thank you for your patience",
        "continue to hold",
        "high call volume",
        "music",
        "queue",
    )

    def __init__(self, threshold: float = 0.72) -> None:
        self.threshold = threshold

    def evaluate(self, text: str) -> Detection:
        normalized = text.lower().strip()
        if not normalized:
            return Detection(False, 0.0, "empty transcript")

        for phrase in self.strong_phrases:
            if phrase in normalized:
                return Detection(True, 0.9, f"strong hold phrase: {phrase}")

        weak_matches = [phrase for phrase in self.weak_phrases if phrase in normalized]
        confidence = min(0.35 + (0.18 * len(weak_matches)), 0.85)
        return Detection(confidence >= self.threshold, confidence, "weak hold phrases: " + ", ".join(weak_matches))


class RepresentativeDetector:
    positive_phrases = (
        "thanks for holding",
        "thank you for holding",
        "how can i help",
        "how may i help",
        "how can i assist",
        "how may i assist",
        "what can i help",
        "this is",
        "my name is",
        "who am i speaking with",
        "can i get your",
        "what is the reason for your call",
    )
    negative_phrases = (
        "your call is important",
        "next available",
        "estimated wait time",
        "please continue to hold",
        "remain on the line",
        "press",
        "main menu",
    )

    def __init__(self, threshold: float = 0.68) -> None:
        self.threshold = threshold

    def evaluate(self, text: str) -> Detection:
        normalized = text.lower().strip()
        if not normalized:
            return Detection(False, 0.0, "empty transcript")

        negative_matches = [phrase for phrase in self.negative_phrases if phrase in normalized]
        if negative_matches:
            return Detection(False, 0.15, "negative representative phrase: " + ", ".join(negative_matches))

        for phrase in self.positive_phrases:
            if phrase in normalized:
                return Detection(True, 0.86, f"representative phrase: {phrase}")

        question_like = normalized.endswith("?") or any(token in normalized for token in ("account number", "date of birth", "member id"))
        confidence = 0.7 if question_like and len(normalized.split()) >= 4 else 0.25
        return Detection(confidence >= self.threshold, confidence, "question-like representative speech")

