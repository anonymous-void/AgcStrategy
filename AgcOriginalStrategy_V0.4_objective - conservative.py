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
    def __init__(self, ts_p_theory, capacity, wind_or_solar='Wind'):
        self.dv_p_theory = ts_p_theory
        self.d_capacity = capacity
        self.d_p_delta = 0.1 * self.d_capacity
        self.d_real_out = 0
        self.d_upbility = 0  # whether it can generate more power 0:No 1:Yes
        self.d_p_base = 0
        self.type = wind_or_solar
        self.random_mu = 0.0
        self.random_sigma = 0.05/3.0  ## 5%的误差，除以3是3sigam原则

    def RealOutput(self, d_p_ref, t_step):
        # self.d_real_out = np.min([d_p_ref, self.dv_p_theory[t_step]]) * (1 + np.random.normal(self.random_mu, self.random_sigma))  # 指令值基础上添加误差
        self.d_real_out = np.min([d_p_ref, self.dv_p_theory[t_step]]) + \
                          self.d_capacity * np.random.normal(self.random_mu, self.random_sigma)   # 输出值基础上添加误差
        return self.d_real_out


class AgcMaster:
    def __init__(self, p_limit, agc_obj_dict):
        self.P_LIMIT = p_limit
        self.TotalCapacity = 0
        self.T_SPAN = len(list(agc_obj_dict[list(agc_obj_dict.keys())[0]].dv_p_theory))
        self.AgcSiteAmount = len(agc_obj_dict)
        self.AgcObjDict = agc_obj_dict

        self.dic_p_ref_rec = dict()
        self.dic_p_real_rec = dict()
        self.dic_catchup_rec = dict()
        self.dic_catch_mode_rec = dict()
        self.dic_p_real_free_rec = dict()   # ugly, need change
        self.dic_distmode_rec = list()  # distribution mode has no means for each sites, only mean to the whole sites

        for key in agc_obj_dict:
            self.dic_p_ref_rec[key] = list()
            self.dic_p_real_rec[key] = list()
            self.dic_catchup_rec[key] = list()
            self.dic_catch_mode_rec[key] = list()

        for key in self.AgcObjDict:
            self.TotalCapacity += self.AgcObjDict[key].d_capacity
        # for key in self.AgcObjDict:
        #     self.AgcObjDict[key].d_p_base = self.AgcObjDict[key].d_capacity * self.P_LIMIT / self.TotalCapacity
        self.PbaseRedistribute(which_type=['Wind', 'Solar'])

    def PbaseRedistribute(self, which_type=['Wind', 'Solar']):
        # This prog redistribute p_base based on  _type_  specification
        tmp_total = 0
        for key in self.AgcObjDict:
            if self.AgcObjDict[key].type in which_type:
                tmp_total += self.AgcObjDict[key].d_capacity
        for key in self.AgcObjDict:
            if self.AgcObjDict[key].type in which_type:
                self.AgcObjDict[key].d_p_base = self.AgcObjDict[key].d_capacity * self.P_LIMIT / tmp_total
            else:
                self.AgcObjDict[key].d_p_base = 0

    def DayOrNight(self, t_step, day_or_night_seq):
        if day_or_night_seq[t_step] == 1:
            # day
            return 'day'
        else:
            return 'night'

    def DayNightSequenceGen(self):
        daynight_dot = [x for x in range(self.T_SPAN) if x % 360 == 0 and x % 720 != 0]
        def tmp_day_or_night(t_step):
            num = 0
            for item in daynight_dot:
                if item < t_step:
                    num += 1
            if num % 2 == 0:
                return 0
            else:
                return 1
        tmp = list()
        for i in range(0, self.T_SPAN):
            tmp.append( tmp_day_or_night(i) )
        return tmp


    def CatchUpCheck(self, d_tmp_p_real, d_tmp_p_ref):
        # A float number will be returned representing whether the site can catch up with the AGC-ref or not
        return np.double(np.abs(d_tmp_p_real - d_tmp_p_ref) <= 1.5)  # less than 1.5MW, then it can catch up

    def CatchUpMode(self, d_tmp_p_real, d_tmp_p_ref):
        if np.double(np.abs(d_tmp_p_real - d_tmp_p_ref) <= 1.5):
            moderet = 'Inbound'
        elif d_tmp_p_real - d_tmp_p_ref > 1.5:
            moderet = 'Surmount'
        else:
            moderet = 'Fallbehind'
        return moderet

    def DictSumUp(self, input_dict):
        ## Universal Dict type sum-up func
        ret = np.double(0)
        for key in input_dict:
            ret += input_dict[key]
        return ret

    def AgcRealOutSumUp(self):
        ret = np.double(0)
        for key in self.AgcObjDict:
            ret += self.AgcObjDict[key].d_real_out
        return ret

    def AgcCatchModeRealOutSumUp(self, which_mode_to_sum_up, t_step):
        # according to catchup mode, sum up the real out
        ret = np.double(0)
        for key in self.AgcObjDict:
            if self.CatchUpMode(self.AgcObjDict[key].d_real_out, self.dic_p_ref_rec[key][t_step - 1]) == which_mode_to_sum_up:
                ret += self.AgcObjDict[key].d_real_out
            else:
                pass  # Nothing to do
        return ret

    def DistributeRef(self, t_step, day_or_night):
        dic_tmp_p_ref = dict()
        # Step1: Add upward margin or not
        #   case1: < 90% channel limit? then add 10% upward margin
        if self.AgcRealOutSumUp() < 0.9 * self.P_LIMIT:
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
        if tmp_ref_sum > self.P_LIMIT:
            mode = mode + 10
            for key in self.AgcObjDict:
                dic_tmp_p_ref[key] = dic_tmp_p_ref[key] * self.P_LIMIT / tmp_ref_sum
        else:
            pass  # pass intended here
        self.dic_distmode_rec.append(mode)

        ret_catchup_mode = dict()
        for key in self.AgcObjDict:
            if t_step == 0:
                ret_catchup_mode[key] = \
                    self.CatchUpMode(self.AgcObjDict[key].d_real_out, 0)
            else:
                ret_catchup_mode[key] = \
                    self.CatchUpMode(self.AgcObjDict[key].d_real_out, self.dic_p_ref_rec[key][t_step - 1])

        # At night, solar panels are off
        if day_or_night == 'night':
            for key in self.AgcObjDict:
                if self.AgcObjDict[key].type == 'Solar':
                    dic_tmp_p_ref[key] = 0
        return dic_tmp_p_ref, mode, ret_catchup_mode

    # def DistributeRef(self, t_step, day_or_night):
    #     dic_tmp_p_ref = dict()
    #     mode = None
    #
    #     # Case 1: < LIMIT
    #     if self.AgcRealOutSumUp() < 0.98 * self.P_LIMIT:
    #         for key in self.AgcObjDict:
    #         # Case 1.1: <= P_base
    #             if self.AgcObjDict[key].d_real_out < self.AgcObjDict[key].d_p_base:
    #                 mode = 1.1
    #                 dic_tmp_p_ref[key] = np.min([self.AgcObjDict[key].d_real_out + self.AgcObjDict[key].d_p_delta, self.AgcObjDict[key].d_p_base])
    #         # Case 1.2: > P_base
    #             else:
    #                 catch_mode = self.CatchUpMode(self.AgcObjDict[key].d_real_out, self.dic_p_ref_rec[key][t_step - 1])
    #             # Case 1.2.1: |P_real - P_ref| <= epsilon
    #                 if catch_mode == 'Inbound':
    #                     mode = 1.21
    #                     dic_tmp_p_ref[key] = self.AgcObjDict[key].d_real_out + \
    #                         (self.AgcObjDict[key].d_real_out / self.AgcCatchModeRealOutSumUp('Inbound', t_step)) * \
    #                                          (self.P_LIMIT - self.AgcRealOutSumUp())
    #             # Case 1.2.2: P_real - P_ref < -epsilon, it CAN'T catch
    #                 elif catch_mode == 'Fallbehind':
    #                     mode = 1.22
    #                     dic_tmp_p_ref[key] = self.AgcObjDict[key].d_real_out + \
    #                         (self.dic_p_ref_rec[key][t_step - 1] - self.dic_p_real_rec[key][t_step - 1])
    #             # Case 1.2.3: P_real - P_ref > epsilon, yes it can catch
    #                 else:  # Surmount
    #                     dic_tmp_p_ref[key] = self.AgcObjDict[key].d_real_out
    #
    #             # ref < capacity
    #             if dic_tmp_p_ref[key] > self.AgcObjDict[key].d_capacity:
    #                 dic_tmp_p_ref[key] = self.AgcObjDict[key].d_capacity
    #     # Case 2: ~= LIMIT
    #     elif self.AgcRealOutSumUp() <= self.P_LIMIT:
    #         for key in self.AgcObjDict:
    #             # Case 2.1: <= P_base
    #             if self.AgcObjDict[key].d_real_out <= self.AgcObjDict[key].d_p_base:
    #                 mode = 2.1
    #                 dic_tmp_p_ref[key] = \
    #                     np.min([self.AgcObjDict[key].d_real_out + self.AgcObjDict[key].d_p_delta,
    #                             self.AgcObjDict[key].d_p_base])
    #             # Case 2.2: > P_base
    #             else:
    #                 mode = 2.2
    #                 dic_tmp_p_ref[key] = self.AgcObjDict[key].d_real_out
    #
    #             # ref < capacity
    #             if dic_tmp_p_ref[key] > self.AgcObjDict[key].d_capacity:
    #                 dic_tmp_p_ref[key] = self.AgcObjDict[key].d_capacity
    #
    #     # Case 3: > LIMIT
    #     else:
    #         mode = 3
    #         for key in self.AgcObjDict:
    #             dic_tmp_p_ref[key] = self.AgcObjDict[key].d_real_out + \
    #                                  (self.AgcObjDict[key].d_real_out / self.AgcRealOutSumUp()) * \
    #                                  (self.P_LIMIT - self.AgcRealOutSumUp())
    #
    #     ret_catchup_mode = dict()
    #     for key in self.AgcObjDict:
    #         if t_step == 0:
    #             ret_catchup_mode[key] = \
    #                 self.CatchUpMode(self.AgcObjDict[key].d_real_out, 0)
    #         else:
    #             ret_catchup_mode[key] = \
    #                 self.CatchUpMode(self.AgcObjDict[key].d_real_out, self.dic_p_ref_rec[key][t_step - 1])
    #
    #     # At night, solar panels are off
    #     if day_or_night == 'night':
    #         for key in self.AgcObjDict:
    #             if self.AgcObjDict[key].type == 'Solar':
    #                 dic_tmp_p_ref[key] = 0
    #
    #
    #
    #     return dic_tmp_p_ref, mode, ret_catchup_mode



    def MainLoop(self):
        dic_tmp_p_ref = dict()
        tmp_day_or_night = 'night'  # for day-night change and log
        tmp_day_or_night_seq = self.DayNightSequenceGen()

        for key in self.AgcObjDict:
            dic_tmp_p_ref[key] = 0

        for idx in range(self.T_SPAN):
            print('Limit = %i -- Progress: %8.5f %%' % (self.P_LIMIT, 100*(idx+1)/self.T_SPAN))
            # Redistribute p_base based on Day or Night

            if self.DayOrNight(idx, day_or_night_seq=tmp_day_or_night_seq) != tmp_day_or_night:
                if tmp_day_or_night == 'night':
                    self.PbaseRedistribute(which_type=['Wind', 'Solar'])
                    tmp_day_or_night = 'day'
                else:
                    self.PbaseRedistribute(which_type=['Wind'])
                    tmp_day_or_night = 'night'

            for key in self.AgcObjDict:
                self.AgcObjDict[key].RealOutput(dic_tmp_p_ref[key], t_step=idx)
                self.AgcObjDict[key].d_upbility = \
                    self.CatchUpCheck(self.AgcObjDict[key].d_real_out, dic_tmp_p_ref[key])
            dic_tmp_p_ref, dic_tmp_distmode, dic_tmp_catchup_mode = self.DistributeRef(t_step=idx, day_or_night=tmp_day_or_night)


            # Recording intermediate datum
            for key in self.AgcObjDict:
                self.dic_p_ref_rec[key].append(dic_tmp_p_ref[key])
                self.dic_p_real_rec[key].append(self.AgcObjDict[key].d_real_out)
                self.dic_catchup_rec[key].append(self.AgcObjDict[key].d_upbility)
                self.dic_catch_mode_rec[key].append(dic_tmp_catchup_mode[key])

            self.dic_distmode_rec.append(dic_tmp_distmode)




# File import here。 Wind：2298.5（7）x2.181  Solar：2400（16）x5.357

# Step1: Import file list
RootDir = 'D:/Work/新能源工作/[Routine] 未分组工作/20191126-吴所论文送出送出极限对比/'
SiteNameFile = pd.read_excel(RootDir + 'scada/file_list.xlsx')
SiteProcessDict = dict()
for idx in range(len(SiteNameFile)):
    SiteProcessDict[SiteNameFile.iloc[idx]['Name']] = dict()
    SiteProcessDict[SiteNameFile.iloc[idx]['Name']]['Capacity'] = SiteNameFile.iloc[idx]['Capacity']
    SiteProcessDict[SiteNameFile.iloc[idx]['Name']]['Type'] = SiteNameFile.iloc[idx]['Type']
    if SiteProcessDict[SiteNameFile.iloc[idx]['Name']]['Type'] == 'Wind':
        SiteProcessDict[SiteNameFile.iloc[idx]['Name']]['Capacity'] *= 2.181
    else:
        SiteProcessDict[SiteNameFile.iloc[idx]['Name']]['Capacity'] *= 5.357

SiteProcessList = [key for key in SiteProcessDict]

# Step2: Import files ####
SiteFile = dict()
for idx, name in enumerate(SiteProcessList):  # SiteProcessTable
    SiteFile[name] = ScadaFileRead(argFileName=name, argInDir=RootDir + 'scada/')
    print('(' + str(idx+1) + '/' + str(len(SiteProcessList)) + ')' + name)

# Step3: Create time series from file
SiteTsDict = dict()
for name in SiteProcessList:
    if SiteProcessDict[name]['Type'] == 'Wind':
        SiteTsDict[name] = (SiteFile[name]['出力值'] * 2.181).tolist()  # .loc['2017/1/1 00:00:00':'2017/1/31 23:59:00']
    else:
        SiteTsDict[name] = (SiteFile[name]['出力值'] * 5.357).tolist()



if __name__ == '__main__':
    for tmp_limit in [2990, 2980]:
        np.random.seed(0)
        # Step4: Agc object creating
        AgcList = SiteProcessList
        agc_obj_dic = dict()
        for name in AgcList:
            agc_obj_dic[name] = AgcSlave(ts_p_theory=SiteTsDict[name],
                                         capacity=SiteProcessDict[name]['Capacity'], wind_or_solar=SiteProcessDict[name]['Type'])

        master = AgcMaster(p_limit=tmp_limit, agc_obj_dict=agc_obj_dic)
        master.MainLoop()

        real_sum = np.array(master.DictSumUp(master.dic_p_real_rec))
        LimitExceedCounter = np.sum((real_sum - tmp_limit) > 0)  # 超极限点计数器

        OutDir = 'D:/Work/新能源工作/[Routine] 未分组工作/20191126-吴所论文送出送出极限对比/01-Conservative/'

        pd.DataFrame({'RealSum': np.array(real_sum)}).to_csv(OutDir + str(master.P_LIMIT) + "MW" + '-realsum.csv')


        fig, ax = plt.subplots(dpi=300)
        ax.plot(real_sum, label='发电功率(MW)')
        ax.plot([master.P_LIMIT]*len(real_sum), label='控制极限(MW)')
        ax.set_title('控制极限 = ' + str(master.P_LIMIT) + '(MW)')
        ax.set_ylabel('功率(MW)')
        ax.set_xlabel('时间')
        ax.legend(loc='lower right')
        ax.grid()

        fig.savefig(OutDir + str(master.P_LIMIT) + 'MW-' + str(LimitExceedCounter) + '-realsum.png')
        fig.savefig(OutDir + str(master.P_LIMIT) + 'MW-' + str(LimitExceedCounter) + '-realsum.pdf')

