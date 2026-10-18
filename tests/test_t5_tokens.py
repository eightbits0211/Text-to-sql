from text_to_sql.transformer.training import add_sql_tokens


class _Tokenizer:
    unk_token_id = 2

    def __init__(self, known):
        self.known = set(known)
        self.added = []

    def __call__(self, text, add_special_tokens=False):
        class _Out:
            input_ids = [5] if text in self.known else [self.unk_token_id]

        return _Out()

    def add_tokens(self, tokens):
        self.added.extend(tokens)
        return len(tokens)

    def __len__(self):
        return 100 + len(self.added)


class _Model:
    resized = None

    def resize_token_embeddings(self, size):
        self.resized = size


def test_adds_only_missing_sql_tokens_and_resizes():
    tokenizer, model = _Tokenizer(known={"<="}), _Model()
    assert add_sql_tokens(tokenizer, model) == 1
    assert tokenizer.added == ["<"]
    assert model.resized == 101


def test_no_resize_when_nothing_missing():
    tokenizer, model = _Tokenizer(known={"<", "<="}), _Model()
    assert add_sql_tokens(tokenizer, model) == 0
    assert model.resized is None
