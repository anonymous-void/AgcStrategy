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
        self.dv_p_theory = ts_p_theory
        self.d_capacity = capacity
        self.d_p_delta = 0.2 * self.d_capacity
        self.d_real_out = 0
        self.d_upbility = 0  # whether it can generate more power 0:No 1:Yes

    def RealOutput(self, d_p_ref, t_step):
        self.d_real_out = np.min([d_p_ref, self.dv_p_theory[t_step]])
        return self.d_real_out


class FreeSlave:
    def __init__(self, ts_p_theory, capacity, limit):
        self.dv_p_theory = ts_p_theory
        self.d_capacity = capacity
        self.d_real_out = 0
        self.limit = limit

    def RealOutput(self, t_step):
        self.d_real_out = np.min([self.limit, self.dv_p_theory[t_step]])
        return self.d_real_out


class AgcMaster:
    def __init__(self, p_limit, agc_obj_dict, free_obj_dict):
        self.P_LIMIT = p_limit
        self.T_SPAN = len(list(agc_obj_dict[list(agc_obj_dict.keys())[0]].dv_p_theory))
        self.AgcSiteAmount = len(agc_obj_dict)
        self.FreeSiteAmount = len(free_obj_dict)
        self.AgcObjDict = agc_obj_dict
        self.FreeObjDict = free_obj_dict

        self.dic_p_ref_rec = dict()
        self.dic_p_real_rec = dict()
        self.dic_catchup_rec = dict()
        self.dic_p_real_free_rec = dict()   # ugly, need change
        self.dic_distmode_rec = list()  # distribution mode has no means for each sites, only mean to the whole sites

        for key in agc_obj_dict:
            self.dic_p_ref_rec[key] = list()
            self.dic_p_real_rec[key] = list()
            self.dic_catchup_rec[key] = list()

        for key in free_obj_dic:
            self.dic_p_real_free_rec[key] = list()

    def CatchUpCheck(self, d_tmp_p_real, d_tmp_p_ref):
        # A float number will be returned representing whether the site can catch up with the AGC-ref or not
        return np.double(np.abs(d_tmp_p_real - d_tmp_p_ref) <= 1.5)  # less than 1.5MW, then it can catch up

    def DictSumUp(self, input_dict):
        ret = np.double(0)
        for key in input_dict:
            ret += input_dict[key]
        return ret

    def AgcRealOutSumUp(self):
        ret = np.double(0)
        for key in self.AgcObjDict:
            ret += self.AgcObjDict[key].d_real_out
        return ret

    def FreeRealOutSumUp(self):
        ret = np.double(0)
        for key in self.FreeObjDict:
            ret += self.FreeObjDict[key].d_real_out
        return ret

    def DistributeRef(self):
        dic_tmp_p_ref = dict()
        # Step1: Add upward margin or not
        #   case1: < 90% channel limit? then add 10% upward margin
        if self.AgcRealOutSumUp() + self.FreeRealOutSumUp() < 0.9 * self.P_LIMIT:
            mode = 1
            self.dic_distmode_rec.append(mode)
            for key in self.AgcObjDict:
                dic_tmp_p_ref[key] = self.AgcObjDict[key].d_real_out + \
                                          self.AgcObjDict[key].d_p_delta * self.AgcObjDict[key].d_upbility
        #   case2: between [90% +inf] channel limit ? then p_ref_{t+1} = p_real_{t}
        else:
            mode = 5
            self.dic_distmode_rec.append(mode)
            for key in self.AgcObjDict:
                dic_tmp_p_ref[key] = self.AgcObjDict[key].d_real_out

        # Step2: Refactor distribution reference if the sum exceed limit
        # After p_ref distribution, if the p_ref_{t+1} + p_free_out_{t} exceed P_LIMIT? then refactor it
        tmp_ref_sum = self.DictSumUp(dic_tmp_p_ref)
        if tmp_ref_sum + self.FreeRealOutSumUp() > self.P_LIMIT:
            mode = mode + 10
            self.dic_distmode_rec.append(mode)
            for key in self.AgcObjDict:
                dic_tmp_p_ref[key] = dic_tmp_p_ref[key] * (self.P_LIMIT - self.FreeRealOutSumUp()) / tmp_ref_sum
        else:
            pass  # pass intended here

        return dic_tmp_p_ref, mode

    def MainLoop(self):
        dic_tmp_p_ref = dict()
        dic_tmp_p_real = dict()
        dic_tmp_catchup = dict()

        for key in self.AgcObjDict:
            dic_tmp_p_ref[key] = 0
            dic_tmp_p_real[key] = 0
            dic_tmp_catchup[key] = 0

        for idx in range(self.T_SPAN):
            print(idx)
            for key in self.AgcObjDict:
                self.AgcObjDict[key].RealOutput(dic_tmp_p_ref[key], t_step=idx)
                self.AgcObjDict[key].d_upbility = \
                    self.CatchUpCheck(self.AgcObjDict[key].d_real_out, dic_tmp_p_ref[key])
            dic_tmp_p_ref, dic_tmp_distmode = self.DistributeRef()

            for key in self.FreeObjDict:
                self.FreeObjDict[key].RealOutput(t_step=idx)

            # Recording intermediate datum
            for key in self.AgcObjDict:
                self.dic_p_ref_rec[key].append(dic_tmp_p_ref[key])
                self.dic_p_real_rec[key].append(self.AgcObjDict[key].d_real_out)
                self.dic_catchup_rec[key].append(dic_tmp_catchup[key])

            for key in self.FreeObjDict:
                self.dic_p_real_free_rec[key].append(self.FreeObjDict[key].d_real_out)


if __name__ == '__main__':
    slave1 = AgcSlave(ts_1, 45)
    slave2 = AgcSlave(ts_2, 76)
    slave3 = FreeSlave(ts_3, 75, 9999)

    agc_obj_dic = {'agc1': slave1, 'agc2': slave2}
    free_obj_dic = {'free1': slave3}
    # agc_obj_dic = {'agc1': slave1}
    # free_obj_dic = dict()

    master = AgcMaster(p_limit=80, agc_obj_dict=agc_obj_dic, free_obj_dict=free_obj_dic)
    master.MainLoop()

    plt.plot(master.dic_p_ref_rec['agc1'], 'ro', label='agc1-ref')
    plt.plot(ts_1, label='agc1-theory')
    plt.plot(master.dic_p_real_rec['agc1'], label='agc1-real')
    plt.plot(master.dic_p_ref_rec['agc2'], 'co', label='agc2-ref')
    plt.plot(ts_2, label='agc2-theory')
    plt.plot(master.dic_p_real_rec['agc2'], label='agc2-real')
    plt.plot(np.array(master.dic_p_real_rec['agc1']) + np.array(master.dic_p_real_rec['agc2']) +
             np.array(master.dic_p_real_free_rec['free1']), label='real-sum')
    plt.plot(master.dic_p_real_free_rec['free1'], '*', label='free1-real')
    plt.plot(np.array(master.dic_distmode_rec), 'ko', label='distmode')
    plt.plot([80]*len(ts_1), linewidth=5.0, label='Limit')
    plt.legend()
    plt.show()

