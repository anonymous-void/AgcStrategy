import matplotlib.pyplot as plt
import numpy as np
import time
import pandas as pd
import copy as cp


def ScadaFileRead(argFileName, argInDir):
    ScadaFileHand = open(argInDir + argFileName + '.csv')
    ScadaFile = pd.read_csv(ScadaFileHand, index_col=0)
    ScadaFile.columns = ['出力值']
    ScadaFile.index = pd.to_datetime(ScadaFile.index)
    ScadaFile = ScadaFile.resample('min').first()
    ScadaFileHand.close()
    return ScadaFile


AgcDir = 'D:/PJ/Python/JupyterNB/WindPowerAGC/AgcMergedScada/2017/'
ScadaDir = 'D:/PJ/Python/JupyterNB/WindPowerAGC/ScadaSeperated/2016/'

SiteFileRaw = ScadaFileRead('坝头', ScadaDir)

# ts_free = SiteFileRaw.loc['2016/1/9 04:00:00':'2016/1/9 09:00:00']['出力值'].tolist()
ts_1 = SiteFileRaw.loc['2016/1/9 04:00:00':'2016/1/9 09:00:00']['出力值'].tolist()
ts_2 = SiteFileRaw.loc['2016/1/10 04:00:00':'2016/1/10 09:00:00']['出力值'].tolist()

'''
Global var zone
'''
'''
Function zone
default input vector using np.array
'''
'''
Class def zone
'''
class AgcSlave:
    def __init__(self, ts_p_theory):
        self.dv_p_theory = iter(ts_p_theory)

    def real_output(self, d_p_ref):
        ret = np.min([d_p_ref, self.dv_p_theory.__next__()])

        return


def flat(nested):
    for item in nested:
        yield item
# def f_site_real_output(dv_p_ref, dv_p_theory):
#     return np.min([dv_p_ref, dv_p_theory], axis=0)
#
#
# def f_agc_dist_ref(d_p_limit, dv_p_real, dv_p_delta, bv_up_ability):
#     # step 1: add upward power margin depends on the sites' status
#     dv_p_real_next = dv_p_real + dv_p_delta * bv_up_ability
#     # step 2: refactor dv_p_real_next if sum of p^{real}_{i, t+1} exceed limitation
#     if np.sum(dv_p_real_next) > d_p_limit:
#         dv_p_real_next = dv_p_real_next * d_p_limit / np.sum(dv_p_real_next)
#     return dv_p_real_next
#
#
# def f_agc_catch_up_verify(dv_p_ref, dv_p_real):
#     # An array will be returned representing whether the site can catch up with the AGC-ref or not
#     return np.double(dv_p_real > dv_p_ref)


if __name__ == '__main__':
    nest = [[1, 2], [3, 4], [5]]
    slave1 = AgcSlave(ts_1)
    # P_LIMIT = 30
    # tmp_p_ref_next = 0
    # P_DELTA = 20
    # p_real = list()
    # for idx in range(len(ts_1)):
    #     tmp_p_real = f_site_real_output(np.array([tmp_p_ref_next]), np.array(ts_1)[idx])
    #     tmp_catch_up = f_agc_catch_up_verify(tmp_p_ref_next, tmp_p_real) # this func could have different sample time
    #     tmp_p_ref_next = f_agc_dist_ref(P_LIMIT, tmp_p_real, P_DELTA, np.array([1]))
    #     p_real.append(tmp_p_real)
    #
    # plt.plot(ts_1, label='theory')
    # plt.plot(p_real, label='real')
    # plt.legend()
    # plt.show()
