from dazer_methods import Dazer
from lib.Astro_Libraries.Abundances_InferenceModel_Helium_v18punto5 import Run_MCMC

#MCMC configuration run
default_db_folder   = '/home/vital/Astrodata/Inference_output/'
db_name_ext         = 'He_S_O_HbetaAdj_v0'
iterat, burn, thin  = 10000, 1000, 1 #15000, 1500, 2
synth_model         = 'Model3_Metals'
#params_list         = ['y_plus','T_high','T_low','ne','tau','cHbeta','xi','S2_abund','S3_abund','O2_abund','O3_abund']
params_list         = ['y_plus', 'T_low','ne','tau','cHbeta','xi','S2_abund','S3_abund','O2_abund','O3_abund']             

                        #'ChiSq_Recomb','ChiSq_S','ChiSq_O',
#Generate dazer object
dz = Dazer()
bm = Run_MCMC()
  
#Generate the synthetic data
bm.calculate_synthFluxes(synth_model)
     
# #Select right model according to data
bm.select_inference_model(synth_model)     
#             
# #Variables to save
db_address  = '{}5punto5{}_burn{}_thin{}_{}'.format(default_db_folder, iterat, burn, thin, db_name_ext)

print 'Este nombre', db_address
#                 
# # #Run sampler
bm.run_pymc2(db_address, iterat, burn, thin, variables_list=params_list)
# 
# #Load database
# pymc2_db, stat_db_dict = bm.load_pymc_database(db_address)
#  
# #Traces plot
# dz.traces_plot(params_list, pymc2_db, stat_db_dict)
# dz.save_manager(db_address + '_tracesPlot', save_pickle = False)
#   
# #Posteriors plot
# dz.posteriors_plot(params_list, pymc2_db, stat_db_dict)
# dz.save_manager(db_address + '_posteriorPlot', save_pickle = False)
#   
# #Posteriors plot
# dz.acorr_plot(params_list, pymc2_db, stat_db_dict, n_columns=4, n_rows=3)
# dz.save_manager(db_address + '_acorrPlot', save_pickle = False)
#  
# #Corner plot
# dz.corner_plot(params_list, pymc2_db, stat_db_dict)
# dz.save_manager(db_address + '_cornerPlot', save_pickle = False)
#  
# print '\nData treated'

