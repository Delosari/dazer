from dazer_methods import Dazer
from lib.Astro_Libraries.Abundances_InferenceModel_Helium_v21 import Run_MCMC

# default_db_folder   = '/home/vital/Astrodata/Inference_output/'
# iterat, burn, thin  = 5000, 1000, 1
# sim_model           = 'Saving_coeffs'
# sim_components      = '_stellar'
# sim_name            = sim_model + sim_components
# params_list         = ['z_star','sigma_star','Av_star'] #'ChiSq_Recomb','ChiSq_S','ChiSq_O']      

#MCMC configuration run
default_db_folder   = '/home/vital/Astrodata/Inference_output/'
iterat, burn, thin  = 10000, 1500, 2
sim_model           = 'coeffsValid'
sim_components      = '_He_S_O_neb_stellar'
sim_name            = sim_model + sim_components
params_list         = ['y_plus','T_low','ne','tau','cHbeta','xi','S2_abund','S3_abund','O2_abund','O3_abund', 'z_star','sigma_star','Av_star'] #'ChiSq_Recomb','ChiSq_S','ChiSq_O']      
                  
#Generate dazer object
dz = Dazer()
bm = Run_MCMC()

#Generate the synthetic data
bm.calculate_synthFluxes(sim_components)

#Select right model according to data
bm.select_inference_model(sim_components)     
               
# #Variables to save
db_address  = '{}{}_it{}_burn{}_thin{}'.format(default_db_folder, sim_name, iterat, burn, thin) 
   
# #Run sampler
bm.run_pymc2(db_address, iterat, burn, thin, variables_list=params_list)
     
#Load database
pymc2_db, stat_db_dict = bm.load_pymc_database(db_address)
    
#Traces plot
dz.traces_plot(params_list, pymc2_db, stat_db_dict)
dz.save_manager(db_address + '_tracesPlot', save_pickle = False)
      
#Posteriors plot
dz.posteriors_plot(params_list, pymc2_db, stat_db_dict)
dz.save_manager(db_address + '_posteriorPlot', save_pickle = False)
      
#Posteriors plot
dz.acorr_plot(params_list, pymc2_db, stat_db_dict, n_columns=4, n_rows=3)
dz.save_manager(db_address + '_acorrPlot', save_pickle = False)
     
#Corner plot
dz.corner_plot(params_list, pymc2_db, stat_db_dict)
dz.save_manager(db_address + '_cornerPlot', save_pickle = False)
    
print '\nData treated'
