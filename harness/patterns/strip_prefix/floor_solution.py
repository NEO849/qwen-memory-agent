"""FLOOR — the naive implementation a model plausibly writes WITHOUT the memory.

Asked to "strip the /api/ prefix off the path", the obvious move is `path.strip("/api/")`.
It reads like it removes the prefix and passes a hand-check on a friendly example — but
`str.strip` removes any of the CHARACTERS {'/', 'a', 'p', 'i'} from *both* ends, so
"/api/pipeline" becomes "eline" and "/health" loses its leading slash. Genuinely how these
bugs ship; not deliberately broken.
"""


def clean_path(path):
    return path.strip("/api/")
