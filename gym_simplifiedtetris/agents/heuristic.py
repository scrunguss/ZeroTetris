import numpy as np


class HeuristicAgent(object):
    """
    A class representing an agent that selects the action with the largest heuristic score.
    """

    @staticmethod
    def predict(ratings_or_priorities: np.array) -> int:
        """
        Returns the action that yields the largest heuristic score. Ties are separated by a priority rating based on the translation and rotation.

        :param heuristic_scores: the heuristic scores for each action.
        :return: the action with the largest heuristic score.
        """

        return np.argmax(ratings_or_priorities)
