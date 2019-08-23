# Package: Pandas
import pandas as pd
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
