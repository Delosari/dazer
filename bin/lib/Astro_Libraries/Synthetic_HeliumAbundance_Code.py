#!/usr/bin/python

import pymc

from Astro_Libraries.Abundances_InferenceModel_Helium_v4    import HeAbundance_InferenceStructure
from CodeTools.PlottingManager                              import myPickle


#Default address to store the data
Databases_Folder    = '/home/vital/Workspace/X_ModelData/MCMC_databases/' 
Db_name             = 'he_Abundance_10000_Hope8'
Db_global_file_name = 'he_Abundance_Global_10000_Hope8'

#Generate dazer object
pv = myPickle()
bm = HeAbundance_InferenceStructure()

#Define plot frame and colors
pv.FigFormat_One(ColorConf = 'Night1')

#Declare synthetic data
bm.Import_Synthetic_Fluxes(Model = 'Model2')

#Check the observational data for Hydrogen and Helium lines which can be used for the analysis:
bm.Check_EmissionLinesObserved(bm.SyntheticData_dict)

#Load the data into vectors for the MCMC
bm.Preload_Data(Hbeta_Normalized = True)

#Declare the MCMC dictionary
MCMC_dict = bm.Bayesian_HeliumAbundance_Analysis(bm.H_He_Obs_Flux, bm.H_He_Obs_Error)
  
#Run MCMC
# M = pymc.MCMC(MCMC_dict, db = 'pickle', dbname = Databases_Folder + Db_name)
# M.sample(iter=10000)
# M.write_csv(Databases_Folder + Db_global_file_name, variables=['ChiSq', 'He_abud', 'T_e', 'n_e','abs_H', 'abs_He', 'Tau', 'c_Hbeta', 'Xi'])
# M.db.close()

#Run MCMC with MAP
MAP_Model           = pymc.MAP(MCMC_dict)
MAP_Model.fit() 
M                   = pymc.MCMC(MCMC_dict, db = 'pickle', dbname =  Databases_Folder + Db_name)
M.sample(iter=10000)
M.write_csv(Databases_Folder + Db_global_file_name, variables=['ChiSq', 'He_abud', 'T_e', 'n_e','abs_H', 'abs_He', 'Tau', 'c_Hbeta', 'Xi'])
M.db.close() 

print 'Analysis completed'