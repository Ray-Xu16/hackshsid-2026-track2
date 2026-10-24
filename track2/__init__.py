"""Track 2 model package: inputs, schedulers, energy balance, metrics.

Layout rule of this package: it only holds the *model*. Anything that writes
files or prints tables lives in ``experiments/``, and every directory it touches
is declared once in :mod:`track2.paths`.
"""

__all__ = ["paths", "inputs", "scheduler", "balance", "metrics", "strategies",
           "validation", "config", "reporting"]
