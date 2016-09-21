import random


class RandomChapterID:
    """Class for generating chapter IDs required in Matroska
    chapter XML files.  The class itself mainly consists of
    the class attribute ``ids`` which is a ``list[int]``.
    The constructor accepts one parameter, ``n``, to control
    how many IDs to generate.  If the constructor is called
    multiple times, the class member is only updated if the
    ``n`` parameter is greater than the current size of the
    ``ids`` member (plus one).  Creation of additional IDs
    in this manner is order-preserving such that ``ids[i]``
    is the same before and after for all ``[i]`` valid in
    the old range.

    Requesting a new ``RandomChapterID`` object with ``n``
    smaller than the length of the generated IDs results in
    observing only the first ``n``.  This is handled via the
    ``GetID`` method which is used by ``__getitem__``.
    """
    ids = []
    
    def __init__(self, n):
        self.n = n + 1
        if len(RandomChapterID.ids) > self.n:
            return
        # Note this creates an additional element
        # Can use this for TrackUID
        old_ids = RandomChapterID.ids
        ids = set(RandomChapterID.ids)
        while len(ids) < self.n:
            ids.add(RandomChapterID.RandomID())
        new_ids = ids - set(old_ids)
        RandomChapterID.ids += list(new_ids)

    @staticmethod
    def RandomID():
        """Generates a random 16 digit integer"""
        return int(random.uniform(10**15, 10**16 - 1))

    def GetID(self, n):
        return RandomChapterID.ids[0:self.n][n]

    def __getitem__(self, n):
        # Use ``[0:self.n]`` so that smaller sized RandomChapterID
        # objects see a logical set of IDs such that ``n = -1``
        # returns something in the range ``[0:self.n]``
        return self.GetID(n)
