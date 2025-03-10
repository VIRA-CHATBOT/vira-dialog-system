#
# Copyright 2020-2023 IBM Inc. All rights reserved
# SPDX-License-Identifier: Apache2.0
#

import numpy as np
from tools.db_manager import DBManager
from tools.service_utils import get_scores
import pandas as pd

class KpMatching:

    def __init__(self):

        configuration = DBManager().read_configuration()
        self.url = configuration.get_kp_matching_endpoint()
        self.confidence = configuration.get_kp_matching_confidence()
        self.idx_to_label = DBManager().read_kp_idx_mapping()

    def get_kps(self, indices):
        return [self.idx_to_label[i] for i in indices]

    def is_confident(self, score):
        return score > self.confidence

    # deleting ids not in response db
    def remove_kps_not_in_response_db(self, kps, kp_scores, response_db_kps):
        not_supported_ids = [i for i, kp in enumerate(kps) if kp not in response_db_kps]
        kps = [kp for i, kp in enumerate(kps) if i not in not_supported_ids]
        kp_scores = [kp_score for i, kp_score in enumerate(kp_scores) if i not in not_supported_ids]
        return kps, kp_scores

    def get_top_k_kps(self, arg, k, disable_cache, response_db_kps=None):
        kps, kp_scores = get_scores(self.url, arg, disable_cache)
        if response_db_kps is not None:
            kps, kp_scores = self.remove_kps_not_in_response_db(kps, kp_scores, response_db_kps)
        return kps[:k], kp_scores[:k]

    # matches between a given list of args and the existing kp list
    # for each arg, returns:
    # "confident_kps" - existing kps for which the matching score was above the model thr
    # "top_kps" - the top 3 existing kps
    # "top_scores" - the scores of the top 3 existing kps
    def match_to_existing_kps(self, args):
        kp_scores = np.array(get_scores(self.url, [[arg] for arg in args], 32, disable_cache=True))
        kp_ids = np.array(-kp_scores).argsort()
        # for each kp, creating a list of the kps on which the kp matching score is above the confidence threshold
        confident_matches = [self.get_kps([j for j in kp_ids_list if self.is_confident(kp_scores[i,j])])  for i, kp_ids_list in enumerate(kp_ids)]
        # for each kp, creating a dictionary of all (kp, score) pairs
        all_matches_scores = [dict(zip(kp, score)) for kp, score in
                              zip([self.get_kps(kp_ids_list) for kp_ids_list in kp_ids],
                                  [kp_scores[i, ids] for i,ids in enumerate(kp_ids)])]
        return confident_matches, all_matches_scores


def main():
    kp_matching = KpMatching()
    path = 'data/new_kps.csv'
    df = pd.read_csv(path)
    sents = df['kp'].tolist()
    from components.response_db import ResponseDB
    con_kps = ResponseDB().get_con_kps()
    kp_matches = kp_matching.match_to_existing_kps(sents)
    kp_matches['arg'] = sents
    pd.DataFrame(kp_matches).to_csv('test.csv', index=False)


if __name__ == "__main__":
    main()
