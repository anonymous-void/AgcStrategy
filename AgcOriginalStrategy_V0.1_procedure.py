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

# SiteList = ['红松', '坝头']
# SiteCap = [50.0, 200.0, 48.0]
# SiteCapSum = np.sum(SiteCap)
#
# # 装机容量字典
# SiteCapDict = dict(zip(SiteList, SiteCap))
# # 指令值
# SiteRef = dict(zip(SiteList, [0 for i in range(len(SiteList))]))
# # 通道极限
# ChannelLimit = 130.0
#
# SiteDict = dict()
# for item in SiteList:
#     SiteDict[item] = ScadaFileRead(item, ScadaDir)
#
#
# fig, ax = plt.subplots()
#
# ts = SiteDict['坝头'].loc['2016/1/9 04:00:00':'2016/1/9 04:59:00']['出力值']
# p_base_pre = 0
# p_agc_pre = 0
# p_real_pre = ts.iloc[0]
#
# p_base_now = 30
# p_agc_now = 0
# p_real_now = 0
#
# p_free = 0
# p_channel = 1000000
# p_delta = 0.001
#
# for idx in range(len(ts)):
#     p_free = ts.iloc[idx]
#
#     if p_real_pre < p_base_pre:
#         p_agc_now = cp.deepcopy(p_base_pre)
#     else:  # 发电能力能达到基准值，具备增发条件
#         if p_real_pre >= p_agc_pre:  # 具备
#             p_agc_now = min(p_real_pre + p_delta, p_base_pre + p_channel)
#         else:
#             p_agc_now = p_real_pre + p_delta
#
#     p_agc_pre = cp.deepcopy(p_agc_now)
#     p_base_pre = cp.deepcopy(p_base_now)
#     p_real_pre = min(p_agc_now, p_free)
#     ax.scatter(idx, p_base_now, c='r', s=2)
#     ax.scatter(idx, p_free, c='k', s=2)
#     ax.scatter(idx, p_agc_now, c='b', s=2)
#     ax.scatter(idx, p_real_now, c='c', s=2)

SiteFileRaw = ScadaFileRead('坝头', ScadaDir)

ts_free = SiteFileRaw.loc['2016/1/9 04:00:00':'2016/1/9 09:00:00']['出力值'].tolist()
# print(ts_free)
# SiteFileRaw.loc['2016/1/9 04:00:00':'2016/1/9 09:00:00'].to_csv('p_free.csv')


ts_len = len(ts_free)

p_base = 30.0
p_extra = 35.0

p_agc_now = cp.deepcopy(p_base)
p_agc_next = 0

p_real_now = 0
p_real_next = 0

p_free = 0
delta = 0.5

agc_cache = list()
real_cache = list()

for idx in range(ts_len):
    p_free = cp.deepcopy(ts_free[idx])
    p_real_now = min(p_agc_now, p_free)
    if abs(p_agc_now - p_real_now) < 0.00001:  # 能追踪得上
        if p_agc_now > p_extra: # 超出了增发额度的限制
            p_agc_now = cp.deepcopy(p_extra)
        else:
            p_agc_next = p_real_now + delta
    else: # 追踪不上
        if p_real_now < p_base:
            p_agc_next = cp.deepcopy(p_base)
        else:
            p_agc_next = p_real_now + delta
    agc_cache.append(p_agc_now)
    real_cache.append(p_real_now)
    print('agc = %f, out = %f, free = %f' % (p_agc_now, p_real_now, p_free))

    p_agc_now = cp.deepcopy(p_agc_next)

tx = [i for i in range(ts_len)]

plt.plot(tx, agc_cache, tx, real_cache)
plt.show()


# num = 200
#
# x = np.linspace(0, 10*np.pi, num)
# y = np.sin(x)
# yn = np.array([None]*num)
#
# plt.ion()
# fig = plt.figure()
# ax = fig.add_subplot(111)
# line1, = ax.plot(x, yn, 'r-')
# ax.set_xlim(0, 10*np.pi)
# ax.set_ylim(-2, 2)
#
#
# for idx in range(num):
#     yn[idx] = y[idx]
#     line1.set_ydata(yn)
#     fig.canvas.draw()
#     fig.canvas.flush_events()
