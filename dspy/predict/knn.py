from concurrent.futures import ThreadPoolExecutor
from typing import List, TYPE_CHECKING

import numpy as np

import dsp

if TYPE_CHECKING:
    import dspy


class KNN:
    def __init__(self, k: int, trainset: List["dspy.Example"], vectorizer=None, lazy=True):
        """
        A k-nearest neighbors retriever that finds similar examples from a training set.

        Args:
            k: Number of nearest neighbors to retrieve
            trainset: List of training examples to search through
            vectorizer: Optional dspy.Embedder for computing embeddings. If None, uses sentence-transformers.

        Example:
            >>> trainset = [dsp.Example(input="hello", output="world"), ...]
            >>> knn = KNN(k=3, trainset=trainset)
            >>> similar_examples = knn(input="hello")
        """
        import dspy

        self.k = k
        self.trainset = trainset
        self.embedding = vectorizer or dspy.Embedder(dsp.SentenceTransformersVectorizer())
        if not lazy:
            self.embed()

    def embed(self):
        trainset_casted_to_vectorize = [
            " | ".join([f"{key}: {value}" for key, value in example.items() if key in example._input_keys])
            for example in self.trainset
        ]
        self.trainset_vectors = self.embedding(trainset_casted_to_vectorize).astype(np.float32)

    def __call__(self, **kwargs) -> List["dspy.Example"]:
        if not hasattr(self, "trainset_vectors"):
            self.embed()

        input_example_vector = self.embedding([" | ".join([f"{key}: {val}" for key, val in kwargs.items()])])
        scores = np.dot(self.trainset_vectors, input_example_vector.T).squeeze()
        nearest_samples_idxs = scores.argsort()[-self.k :][::-1]
        train_sampled = [self.trainset[cur_idx] for cur_idx in nearest_samples_idxs]
        return train_sampled


def load_knn_embeddings(program, num_threads=6):
    knns = [p.retrieve_demos for p in program.predictors() if hasattr(p, "retrieve_demos")]

    def do_hydrate(knn):
        knn.embed()

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        list(executor.map(do_hydrate, knns))
