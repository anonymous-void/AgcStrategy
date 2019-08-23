import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['font.serif'] = ['SimHei']
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
import numpy as np
import time
import pandas as pd
import copy as cp
import os

def AgcFileRead(argFileName, argInDir):
    AgcFileHand = open(argInDir + argFileName + '.csv')
    AgcFile = pd.read_csv(AgcFileHand, index_col=0)
    AgcFile.index = pd.to_datetime(AgcFile.index)
    AgcFile = AgcFile.resample('min').first()
    AgcFileHand.close()
    return AgcFile

def ScadaFileRead(argFileName, argInDir):
    ScadaFileHand = open(argInDir + argFileName + '.csv')
    ScadaFile = pd.read_csv(ScadaFileHand, index_col=0)
    ScadaFile.columns = ['出力值']
    ScadaFile.index = pd.to_datetime(ScadaFile.index)
    ScadaFile = ScadaFile.resample('min').first()
    ScadaFileHand.close()
    return ScadaFile


# AgcDir = 'D:/PJ/Python/JupyterNB/WindPowerAGC/AgcMergedScada/2017/'

ScadaDir = 'scada/'

# SiteFileRaw = AgcFileRead('坝头风电场', ScadaDir)


# ts_1 = SiteFileRaw.loc['2016/1/9 04:00:00':'2016/1/9 09:00:00']['出力值'].tolist()
# ts_2 = SiteFileRaw.loc['2016/1/10 04:00:00':'2016/1/10 09:00:00']['出力值'].tolist()
# ts_3 = SiteFileRaw.loc['2016/1/11 04:00:00':'2016/1/11 09:00:00']['出力值'].tolist()
# agc_sites = {'ts1': ts_1, 'ts2': ts_2}
# free_sites = {'ts3': ts_3}
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
            for key in self.AgcObjDict:
                dic_tmp_p_ref[key] = self.AgcObjDict[key].d_real_out + \
                                          self.AgcObjDict[key].d_p_delta * self.AgcObjDict[key].d_upbility
        #   case2: between [90% +inf] channel limit ? then p_ref_{t+1} = p_real_{t}
        else:
            mode = 5
            for key in self.AgcObjDict:
                dic_tmp_p_ref[key] = self.AgcObjDict[key].d_real_out

        # Step2: Refactor distribution reference if the sum exceed limit
        # After p_ref distribution, if the p_ref_{t+1} + p_free_out_{t} exceed P_LIMIT? then refactor it
        tmp_ref_sum = self.DictSumUp(dic_tmp_p_ref)
        if tmp_ref_sum + self.FreeRealOutSumUp() > self.P_LIMIT:
            mode = mode + 10
            for key in self.AgcObjDict:
                dic_tmp_p_ref[key] = dic_tmp_p_ref[key] * (self.P_LIMIT - self.FreeRealOutSumUp()) / tmp_ref_sum
        else:
            pass  # pass intended here
        self.dic_distmode_rec.append(mode)
        return dic_tmp_p_ref, mode

    def MainLoop(self):
        dic_tmp_p_ref = dict()
        dic_tmp_p_real = dict()
        dic_tmp_catchup = dict()

        for key in self.AgcObjDict:
            dic_tmp_p_ref[key] = 0
            dic_tmp_p_real[key] = 0
            # dic_tmp_catchup[key] = 0

        for idx in range(self.T_SPAN):
            print('%8.5f' % (100*(idx+1)/self.T_SPAN))
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
                self.dic_catchup_rec[key].append(self.AgcObjDict[key].d_upbility)

            for key in self.FreeObjDict:
                self.dic_p_real_free_rec[key].append(self.FreeObjDict[key].d_real_out)


if __name__ == '__main__':
    # Step1: Import file list
    SiteNameFile = pd.read_excel('scada/file_list.xlsx')
    SiteProcessTable = dict()
    for idx in range(len(SiteNameFile)):
        SiteProcessTable[SiteNameFile.iloc[idx]['Name']] = dict()
        SiteProcessTable[SiteNameFile.iloc[idx]['Name']]['Capacity'] = SiteNameFile.iloc[idx]['Capacity']
        SiteProcessTable[SiteNameFile.iloc[idx]['Name']]['Free'] = SiteNameFile.iloc[idx]['Free']

    # Step2: Import files ####
    SiteFile = dict()
    for idx, name in enumerate(SiteProcessTable):
        SiteFile[name] = AgcFileRead(argFileName=name, argInDir=ScadaDir)
        print('(' + str(idx+1) + '/' + str(len(SiteProcessTable)) + ')' + name)

    # Step3: Create time series from file
    SiteTsDict = dict()
    for name in SiteProcessTable:
        SiteTsDict[name] = SiteFile[name]['出力值'].tolist()  # .loc['2017/1/10 20:00:00':'2017/1/11 03:00:00']['出力值'].tolist()

    # Step4: Agc object creating
    AgcList = [key for key in SiteProcessTable if SiteProcessTable[key]['Free'] == 0]
    agc_obj_dic = dict()
    for name in AgcList:
        agc_obj_dic[name] = AgcSlave(ts_p_theory=SiteTsDict[name],
                                     capacity=SiteProcessTable[name]['Capacity'])

    # Step5: Free object creating
    FreeList = [key for key in SiteProcessTable if SiteProcessTable[key]['Free'] == 1]
    free_obj_dic = dict()
    for name in FreeList:
        free_obj_dic[name] = FreeSlave(ts_p_theory=SiteTsDict[name],
                                       capacity=SiteProcessTable[name]['Capacity'],
                                       limit=SiteProcessTable[name]['Capacity'])

    master = AgcMaster(p_limit=1100, agc_obj_dict=agc_obj_dic, free_obj_dict=free_obj_dic)
    master.MainLoop()


    real_sum = np.array(master.DictSumUp(master.dic_p_real_rec)) + np.array(master.DictSumUp(master.dic_p_real_free_rec))


    # for key in master.dic_p_real_rec:
    #     plt.plot(master.dic_p_real_rec[key], label=key)

    # plt.plot(SiteTsDict['坝头风电场'], label='theory坝头风电场')
    # plt.plot(master.dic_p_real_rec['坝头风电场'], label='real坝头风电场')
    # plt.plot(master.dic_p_ref_rec['坝头风电场'], label='ref坝头风电场')
    # plt.plot(master.dic_catchup_rec['坝头风电场'], label='catch坝头风电场')
    # plt.plot(master.dic_distmode_rec, label='mode')
    plt.plot(real_sum, label='real_sum')
    plt.plot([1100.0]*len(real_sum))
    plt.legend()
    plt.show()


    # Step5: Save simulation to file

    OutDir = 'D:/Work/新能源工作/[Routine] 未分组工作/20190812-新能源柔直送出极限研究/03-Simulation Result/'
    for idx, name in enumerate(AgcList):
        print('Saving simulation result (%i/%i)' % (idx+1, len(AgcList)))  # progress bar
        ret_dict = dict()
        ret_dict['theory'] = SiteTsDict[name]
        ret_dict['real_out'] = master.dic_p_real_rec[name]
        ret_dict['ref'] = master.dic_p_ref_rec[name]
        ret_dict['catchup'] = master.dic_catchup_rec[name]
        ret_dict['distmode'] = master.dic_distmode_rec
        pd.DataFrame(ret_dict).to_csv(OutDir + name + '.csv')
        # os.system('pause')

    pd.DataFrame({'RealSum': np.array(real_sum)}).to_csv(OutDir + 'realsum.csv')

