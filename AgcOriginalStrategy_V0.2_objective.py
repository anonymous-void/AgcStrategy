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
# ScadaDir = 'D:/PJ/Python/JupyterNB/WindPowerAGC/ScadaSeperated/2016/'
ScadaDir = ''

SiteFileRaw = ScadaFileRead('坝头', ScadaDir)

# ts_free = SiteFileRaw.loc['2016/1/9 04:00:00':'2016/1/9 09:00:00']['出力值'].tolist()
ts_1 = SiteFileRaw.loc['2016/1/9 04:00:00':'2016/1/9 09:00:00']['出力值'].tolist()
ts_2 = SiteFileRaw.loc['2016/1/10 04:00:00':'2016/1/10 09:00:00']['出力值'].tolist()
ts_3 = SiteFileRaw.loc['2016/1/11 04:00:00':'2016/1/11 09:00:00']['出力值'].tolist()
agc_sites = {'ts1': ts_1, 'ts2': ts_2}
free_sites = {'ts3': ts_3}
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
    def __init__(self, ts_p_theory, capacity):
        self.dv_p_theory = iter(ts_p_theory)
        self.d_capacity = capacity
        self.d_p_delta = 0.2 * self.d_capacity

    def real_output(self, d_p_ref):
        return np.min([d_p_ref, self.dv_p_theory.__next__()])

# def flat(nested):
#     for item in nested:
#         yield item

# def f_site_real_output(dv_p_ref, dv_p_theory):
#     return np.min([dv_p_ref, dv_p_theory], axis=0)
#
#
# def f_agc_dist_ref(d_p_limit, dv_p_real, dv_p_delta, bv_up_ability, dv_p_real_free):
#     # case1: < 90% channel limit? then add 10% upward margin
#     if np.sum(dv_p_real) + np.sum(dv_p_real_free) < 0.9 * d_p_limit:
#         dv_p_real_next = dv_p_real + dv_p_delta * bv_up_ability
#         mode = 1
#     # case2: > 90% but < limit? then DO NOT add 10%! simply use previous real output
#     elif np.sum(dv_p_real) + np.sum(dv_p_real_free) < d_p_limit:
#         dv_p_real_next = dv_p_real
#         mode = 2
#     # case3: over limit
#     else:
#         dv_p_real_next = dv_p_real + dv_p_delta * bv_up_ability
#         dv_p_real_next = dv_p_real_next * (d_p_limit - np.sum(dv_p_real_free)) / np.sum(dv_p_real_next)
#         mode = 3
#     return dv_p_real_next, mode

    # # step 1: add upward power margin depends on the sites' status
    # dv_p_real_next = dv_p_real + dv_p_delta * bv_up_ability
    # # step 2: refactor dv_p_real_next if sum of p^{real}_{i, t+1} exceed limitation
    # if np.sum(dv_p_real_next) + np.sum(dv_p_real_free) > d_p_limit:
    #     dv_p_real_next = dv_p_real_next * (d_p_limit - np.sum(dv_p_real_free)) / np.sum(dv_p_real_next)
    # return dv_p_real_next
#
#
# def f_agc_catch_up_verify(dv_p_ref, dv_p_real):
#     # An array will be returned representing whether the site can catch up with the AGC-ref or not
#     return np.double(np.abs(dv_p_real - dv_p_ref) <= 1.5)  # less than 1.5MW, then it can catch up


class AgcMaster:
    def __init__(self, p_limit, agc_obj_dict, free_obj_dict):
        self.P_LIMIT = p_limit
        self.AgcSiteAmount = len(agc_obj_dict)
        self.FreeSiteAmount = len(free_obj_dict)
        self.AgcObjDict = agc_obj_dict
        self.FreeObjDict = free_obj_dict
        self.dic_p_ref_rec = dict()
        self.dic_p_real_rec = dict()
        self.dic_catchup_rec = dict()
        self.dic_distmode_rec = dict()
        for key in agc_obj_dict:
            self.dic_p_ref_rec[key] = list([0])
            self.dic_p_real_rec[key] = list()
            self.dic_catchup_rec[key] = list()
            self.dic_distmode_rec[key] = list()

    def cycle_ss(self):
        for idx in 
        for key in self.AgcObjDict:
            self.dic_p_real_rec[key].append(self.AgcObjDict[key].real_out( ))
        tmp_p_real1 = slave1.real_output(tmp_p_ref_next1)
        tmp_p_real2 = slave2.real_output(tmp_p_ref_next2)
        tmp_catch_up = f_agc_catch_up_verify(np.array([tmp_p_ref_next1, tmp_p_ref_next2]),
                                             np.array([tmp_p_real1, tmp_p_real2]))  # this func could
        tmp_p_ref, mode = f_agc_dist_ref(P_LIMIT, np.array([tmp_p_real1, tmp_p_real2]),
                                         np.array([slave1.d_p_delta, slave2.d_p_delta]),
                                         tmp_catch_up, ts_3[idx])
        tmp_p_ref_next1 = tmp_p_ref[0]
        tmp_p_ref_next2 = tmp_p_ref[1]
        p_ref1.append(tmp_p_ref_next1)
        p_ref2.append(tmp_p_ref_next2)
        p_real1.append(tmp_p_real1)
        p_real2.append(tmp_p_real2)
        dist_mode.append(mode)
        catch_up1.append(tmp_catch_up[0])
        catch_up2.append(tmp_catch_up[1])

    def catchup_check(self, dv_p_ref, dv_p_real):
        # An array will be returned representing whether the site can catch up with the AGC-ref or not
        return np.double(np.abs(dv_p_real - dv_p_ref) <= 1.5)  # less than 1.5MW, then it can catch up

    def dist_ref(self,  dv_p_real, dv_p_delta, bv_up_ability, dv_p_real_free):
        # case1: < 90% channel limit? then add 10% upward margin
        if np.sum(dv_p_real) + np.sum(dv_p_real_free) < 0.9 * self.P_LIMIT:
            dv_p_real_next = dv_p_real + dv_p_delta * bv_up_ability
            mode = 1
        # case2: > 90% but < limit? then DO NOT add 10%! simply use previous real output
        elif np.sum(dv_p_real) + np.sum(dv_p_real_free) < self.P_LIMIT:
            dv_p_real_next = dv_p_real
            mode = 2
        # case3: over limit
        else:
            dv_p_real_next = dv_p_real + dv_p_delta * bv_up_ability
            dv_p_real_next = dv_p_real_next * (self.P_LIMIT - np.sum(dv_p_real_free)) / np.sum(dv_p_real_next)
            mode = 3
        return dv_p_real_next, mode



if __name__ == '__main__':
    slave1 = AgcSlave(ts_1, 45)
    slave2 = AgcSlave(ts_2, 76)
    # AgcMaster(p_limit=100)

    tmp_p_ref_next1 = 0
    tmp_p_ref_next2 = 0

    p_real1 = list()
    p_real2 = list()
    p_ref1 = list()
    p_ref2 = list()
    dist_mode = list()
    catch_up1 = list()
    catch_up2 = list()
    for idx in range(len(ts_1)):
        tmp_p_real1 = slave1.real_output(tmp_p_ref_next1)
        tmp_p_real2 = slave2.real_output(tmp_p_ref_next2)
        tmp_catch_up = f_agc_catch_up_verify(np.array([tmp_p_ref_next1, tmp_p_ref_next2]),
                                             np.array([tmp_p_real1, tmp_p_real2]))  # this func could
        tmp_p_ref, mode = f_agc_dist_ref(P_LIMIT, np.array([tmp_p_real1, tmp_p_real2]),
                                                          np.array([slave1.d_p_delta, slave2.d_p_delta]),
                                                          tmp_catch_up, ts_3[idx])
        tmp_p_ref_next1 = tmp_p_ref[0]
        tmp_p_ref_next2 = tmp_p_ref[1]
        p_ref1.append(tmp_p_ref_next1)
        p_ref2.append(tmp_p_ref_next2)
        p_real1.append(tmp_p_real1)
        p_real2.append(tmp_p_real2)
        dist_mode.append(mode)
        catch_up1.append(tmp_catch_up[0])
        catch_up2.append(tmp_catch_up[1])

    plt.plot(np.array(ts_1)+np.array(ts_2)+np.array(ts_3), label='theory')
    plt.plot(ts_1, label='theory1')
    plt.plot(p_real1, label='real1')
    plt.plot(p_ref1, 'k.', label='ref1')
    plt.plot(np.array(dist_mode)*10, 'ro', label='mode')
    plt.plot(np.array(catch_up1)*15, '*', label='catch1')
    plt.plot(p_real2, label='real2')
    plt.plot(p_ref2, 'k.-', label='ref2')
    plt.plot(ts_3, label='real3')

    plt.plot(np.array(p_real1)+np.array(p_real2)+np.array(ts_3), label='real1+2+3')
    plt.legend()
    plt.show()
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
