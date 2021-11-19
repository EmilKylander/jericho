#!/bin/python3
from Levenshtein import distance as levenshtein_distance


class Diff:
    def check(self, first: str, second: str) -> int:
        """Calculate the difference between two strings"""
        return int(
            100
            * levenshtein_distance(first, second)
            / float(max(len(first), len(second)))
        )
