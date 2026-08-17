import re

_TOKEN_RE = re.compile(r"[a-zA-Zʻʼ'’]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text)]


class Vocabulary:
    """Oddiy bag-of-words lug'ati - token -> indeks."""

    def __init__(self, tokens: list[str]):
        unique = sorted(set(tokens))
        self.token_to_index = {token: idx for idx, token in enumerate(unique)}

    @property
    def size(self) -> int:
        return len(self.token_to_index)

    def vectorize(self, text: str) -> list[float]:
        vector = [0.0] * self.size
        for token in tokenize(text):
            idx = self.token_to_index.get(token)
            if idx is not None:
                vector[idx] = 1.0
        return vector

    @classmethod
    def build(cls, texts: list[str]) -> "Vocabulary":
        all_tokens: list[str] = []
        for text in texts:
            all_tokens.extend(tokenize(text))
        return cls(all_tokens)
